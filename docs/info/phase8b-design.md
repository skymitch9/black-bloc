# Phase 8b design — the full dashboard: tabs, names, settings pages, moderation tools

> **Audience:** the two 8b build agents (API / pages) and the reviewer.
> **Status:** TRACKED (2026-08-31; private repo). **Last verified: 2026-08-26 ~23:00** — written
> against `main` @ `618dcd1` (8a live, sign-in verified by the owner).
> Owner feedback that triggered it, verbatim: *"the who category i assume is
> a discord user id number, that's not helpful we need to resolve that to
> discord username. same with target. … looks great but we need features.
> health can get shoved to a different tab but we need all the moderation
> tool menus."*

## What exists (8a) and stays

Single origin `https://blackbloc.heygabi.ai` served by the bot's FastAPI;
Discord-OAuth session (`__Host-bb_session`), staff gate = the one
computed-permission home; `/api/status`, `/api/actions`, `/api/auth/*`;
static site in `site/public` with the estate theme; security headers; rate
limits. **8b adds writes.** Every write goes through the same code paths the
slash commands use (`SettingsStore.set(..., by=)`, the cogs' storage
helpers, `log_action`), so the audit trail stays one table and the bot sees
changes live. The guard still applies: while `TEST_MODE`, writes that would
act outside the test channel are refused with the same sentence the slash
commands give.

## The contract (both builders code against THIS; do not invent routes)

All routes are under `/api`, JSON, session required (403 `not_staff`,
401 `not_signed_in`, 503 `staff_unknown` as in 8a). Every error body is
`{error, message}` with a sentence. IDs are strings in JSON (snowflakes
overflow JS numbers).

### Reference data (read)

| Route | Returns |
|---|---|
| `GET /api/ref/channels` | `[{id, name, type: text\|voice\|category\|forum, category_id, position}]` from the bot's guild cache |
| `GET /api/ref/roles` | `[{id, name, color, position, managed}]` |
| `GET /api/ref/members?q=&limit=25` | `[{id, name, display_name, avatar_url}]` — cache search; no network |
| `GET /api/ref/names?ids=1,2,3` | `{id: {name, display_name, kind: member\|role\|channel\|unknown}}` — the **name resolver** every table uses |

### Settings (read/write)

| Route | Returns / does |
|---|---|
| `GET /api/settings` | `{namespace: [{key, type, value, default, help, choices?, max?}]}` — namespaces = key prefix before the first `_` (`golive`, `tempvoice`, `honeypot`, `events`, `birthday`, `automod`, `modmail`) plus `core` for `log_channel_id`/`staff_channel_id`/`role_menu_channel_id` |
| `PUT /api/settings/{key}` body `{value}` | `SettingsStore.set` with `by=session user`; returns the stored value; 400 with the validator's sentence on refusal; refuses `TEST_MODE`-sensitive keys? No — settings are data, allowed |
| `DELETE /api/settings/{key}` | `SettingsStore.clear` |
| `GET /api/settings/audit?limit=100` | rows from the `settings` table with `updated_by` resolved |

### Feature tools (read/write)

| Route | Does |
|---|---|
| `GET /api/rolemenus` · `POST /api/rolemenus` · `PUT /api/rolemenus/{name}` · `DELETE …` · `POST /api/rolemenus/{name}/post` body `{channel_id}` | mirrors `/rolemenu create/add/remove/delete/post`; options in the PUT body |
| `GET /api/golive/links` · `DELETE /api/golive/links/{user_id}` · `GET /api/golive/optouts` · `GET /api/golive/sessions?limit=50` | |
| `GET /api/events?status=` · `POST /api/events/{id}/approve` · `POST /api/events/{id}/deny` body `{reason}` · `POST /api/events/{id}/cancel` | same lock + `can_transition` as the buttons |
| `GET /api/birthdays` · `PUT /api/birthdays/{user_id}` · `DELETE …` | |
| `GET /api/tempvoice/channels` · `POST /api/tempvoice/setup` | live list; setup/repair |
| `GET /api/honeypot/hits?limit=` · `POST /api/honeypot/hits/{id}/ban` · `POST /api/honeypot/setup` | ban = the Ban-now path incl. test-mode refusal |
| `GET /api/mod/cases?user_id=&page=` · `GET /api/mod/cases/{id}` · `POST /api/mod/cases/{id}/apply` · `POST /api/mod/warn\|timeout\|kick\|ban\|unban` body `{user_id, reason, duration?}` · `GET /api/mod/rules` · `PUT /api/mod/rules/{name}` · `GET /api/mod/parity?days=` | all through `modcases`/automod helpers; destructive ones return the test-mode refusal sentence with 409 while a guard exists |
| `GET /api/modmail/tickets?status=` · `GET /api/modmail/tickets/{id}` (messages) · `POST /api/modmail/tickets/{id}/reply` body `{text, anonymous}` · `POST …/close` body `{reason, silent}` · `GET/POST/DELETE /api/modmail/snippets` · `GET/POST/DELETE /api/modmail/blocks` | |
| `GET /api/actions?limit=&kind=&user_id=` | as 8a, **plus `actor_name`/`target_name` resolved** and `details` on request |

Write routes log `web.<thing>` action kinds with `actor=session user` so the
action log distinguishes web from slash.

## Pages (site/public) — one HTML per tab, one shared `app.js` + `api.js`

Nav (left rail on wide screens, top tabs on narrow): **Overview · Moderation
· Automod · Modmail · Events · Go-live · Role menus · Birthdays · Temp voice
· Honeypot · Settings · Audit · Health**.

- **Overview** (default, replaces 8a's single page): mode chips per feature
  (click → that feature's tab), open counts, last 10 actions **with names**.
- **Health**: what 8a showed — bot status, uptime, loop health, `/health`.
- **Moderation**: cases table (search by member, paginated), case detail,
  Apply-now; action bar: warn / timeout / kick / ban / unban with a member
  picker (search), reason, duration; parity report with a days input.
- **Automod**: the rule editor (enabled, window, threshold, actions,
  timeout) per rule; exempt roles/channels pickers; mode switch with the
  arming refusal shown as a sentence.
- **Modmail**: open tickets list → ticket view (messages in order, notes
  marked) with reply / anonymous reply / close; snippets; blocks; settings.
- **Events**: queue by status with Approve/Deny(reason)/Cancel; settings.
- **Go-live**: links table (unlink), opt-outs, recent sessions, settings
  with a live template preview.
- **Role menus**: table, editor (options with emoji/label/role picker), post.
- **Birthdays**: list by month, set/remove, import report, settings.
- **Temp voice**: live channels, setup/repair, settings.
- **Honeypot**: hits with Ban-now, setup, settings.
- **Settings**: generic editor for every registry key, grouped by namespace,
  typed inputs (channel/role/member pickers fed by `/api/ref/*`, enum
  selects, bool switches, int/text/color inputs, JSON for `automod_rules`
  only as a fallback).
- **Audit**: the settings audit + `web.*` actions, names resolved.

Every table cell that is a snowflake renders via the name resolver (batch
one `/api/ref/names` call per page load). Every write shows the API's
sentence on failure and the changed value on success; no page reload.
Permission UX rules as 8a (four+one states). Theme dropdown as 8a.

## Split between the two builders

**Builder A — API** (`black_bloc/api/ref.py`, `settings_api.py`,
`tools/*.py` routers, `names.py` resolver), tests under `tests/api/`.
**Builder B — pages** (`site/public/*.html`, `assets/api.js`, `assets/app.js`
per-page modules, `assets/site.css`), tests: a Node-free smoke is fine —
serve locally and exercise against a **mock JSON server** implementing this
contract (write it under `site/mock/`, committed, since the pages' tests
need it). Builder B must not change any API file; Builder A must not change
any site file. Both read this doc as the contract.

## Definition of done

API: green tests incl. a route-gate matrix (every write route refuses
non-staff; destructive routes refuse under guard); pages: every tab renders
against the mock with names, not ids; reviewer merges both and deploys.

## Added 2026-08-27 — the Members tab (`GET /api/members`)

> Owner's ask, verbatim (2026-08-27 10:18): *"also show server users, server
> user count also somewhere in the moderation area."* Built on branch
> `worktree-agent-a85ee9bc21984cdf9` from `main` @ `666dd8e`, commit `feea8d9`.
> **Last verified: 2026-08-27 ~11:20** against `site/mock/server.mjs` and
> `tests/api/tools/test_members.py` — ⚠️ never against live Discord.
>
> The nav is now **fourteen** tabs: Overview · Moderation · **Members** ·
> Automod · Modmail · Events · Go-live · Role menus · Birthdays · Temp voice ·
> Honeypot · Settings · Audit · Health. `site/mock/contract.json` lists 14
> pages and 49 routes.

### The route

| Route | Does |
|---|---|
| `GET /api/members?q=&filter=all\|staff\|bots\|new&page=1&per_page=50&sort=joined_desc\|joined_asc\|name` | the server roster from the bot's member cache, paged. Read-only; same staff gate + read bucket as `/api/mod/*`; no write, so no `web.*` action line and no guard check. |

Query grammar, all read tolerantly (an unknown value falls back rather than
refusing, so a stale bookmark still shows the page):

- `q` — case-insensitive substring over display name, username and global name.
- `filter` — `all` (default) · `staff` · `bots` · `new` (joined ≤ 7 days).
- `page` — 1-based; anything below 1 becomes 1.
- `per_page` — default 50, **capped at 100**.
- `sort` — `joined_desc` (default) · `joined_asc` · `name`. A member with no
  join date sorts **last in both directions**.

Response:

```json
{
  "total": 60,        // guild.member_count — Discord's own figure
  "humans": 56, "bots": 4, "staff": 3, "new_7d": 6,
  "page": 1, "per_page": 50,
  "shown": 50,        // rows on THIS page, from what the cache actually held
  "members": [
    {
      "id": "700000000000000002",
      "name": "Casey",             // display name
      "username": "caseyfast",
      "bot": false,
      "joined_at": "2025-11-02T18:04:00+00:00",   // or null
      "roles": [{"id": "900…", "name": "Leads", "color": "#4eefff"}],
      "staff": true,
      "cases": 3,
      "avatar": "https://cdn.discordapp.com/…"    // or null
    }
  ]
}
```

⚠️ **Every id is a string** (snowflakes overflow JS numbers), role `color` is
`#rrggbb` **or `null`** (Discord's 0 means "no colour", not black), and
`roles` is the top five by position with `@everyone` excluded.

### Where the numbers come from — one home each, no second definitions

| Field | Source |
|---|---|
| membership | `cogs/community/birthdays.py:members_of` — chunks the guild once when the cache is short of `member_count`, logs rather than raising when it cannot |
| `total` | `guild.member_count`; `shown` reports the cache separately rather than one pretending to be the other |
| `staff` | `settings_store.member_is_staff` against `store.staff_role_ids(guild)` — the computed-permission home the sign-in gate uses (checklist item 21). A bot is never counted as staff |
| `cases` | `modcases.count_cases_for` — ONE grouped `IN (…) GROUP BY user_id` for the page's ids; `{}` when the database is down, so the list still renders with `—` |

### The pages that read it

- **`members.html` / `assets/page-members.js`** — stat strip (Members · Humans
  · Bots · Staff · Joined this week), toolbar (search + All/Staff/Bots/New
  chips + "N of M members"), table (Member · Joined · Roles · Cases · chevron),
  pager. A row opens `moderation.html?member=<id>`.
- **`assets/shell.js:memberTally()`** — one `/api/members?per_page=1` per page
  load, cached beside `shellStatus()`, feeding the sidebar's mono count and
  Moderation's fifth stat. `.catch(() => null)`: a stranger gets no count, not
  a broken shell.
- **`assets/page-moderation.js`** — a fifth stat **Members** linking to
  `members.html`, and it now reads `?member=<id>` to filter to one person.

## Routes added by the controls-not-displays follow-up (2026-08-27)

> Built on `worktree-agent-a722f5273a3373659` off `188acf3`. Every one is
> additive, staff-gated by the router's `staff_dependency`, rate-limited by
> `writer_dependency`, refuses in a sentence, and is in `site/mock/contract.json`
> — so `tests/api/test_contract.py` and `site/mock/check.mjs` both cover it.

| Route | Calls | Answers | Refuses |
|---|---|---|---|
| `POST /api/golive/links` | `clean_login`, `link_owner`, `set_link` (`cogs/content/golive.py`) | the link row plus `checked: false` and a `message` | `400 bad_login` for a name `clean_login` rejects · `409 link_taken` (`LINK_TAKEN`) when another member holds that channel |
| `POST /api/golive/optouts` | `set_optout` | `user_id`, `user_name`, `opted_out: true`, `message` | `400 bad_request` for anything that is not an id |
| `DELETE /api/golive/optouts/{user_id}` | `clear_optout` | the same shape with `opted_out: false` | `404 not_opted_out` when they were not on the list |
| `POST /api/birthdays/{user_id}/optin` | `set_opted_in` (`cogs/community/birthdays.py`) | the birthday row plus a `message` | `404 no_birthday` when nobody has that birthday stored |
| `POST /api/tempvoice/forget` | `forget_creator` (`cogs/community/tempvoice.py`, lifted out of the cog's `_forget`) | `forgotten`, `channel_id`, `message` | `404 not_a_lobby` (`NOT_A_LOBBY`, the same sentence `/tempvoice forget` gives) · `400` for a non-id |

⚠️ **`POST /api/golive/links` does NOT check the channel exists on Twitch**, and
says so in its own answer (`checked: false`). The slash command's Helix lookup
has a member in front of it to correct; a staff form does not, and claiming a
check that was skipped is checklist item 10.

⚠️ **The opt-out is removed by path parameter**, not by a DELETE body — it
matches `DELETE /api/golive/links/{user_id}` and `DELETE /api/birthdays/{user_id}`.

New `web.*` action kinds, all in `contract.json`'s `action_kinds`:
`web.golive.link`, `web.golive.optout`, `web.golive.optin`,
`web.birthday.optin`, `web.tempvoice.forget`.

**Not a route, but served differently:** the static mount is
`black_bloc/api/assets.py:SiteFiles` rather than a bare `StaticFiles` — every
`/assets` URL in the HTML is stamped with a build id, HTML is `no-store` and
assets are `no-cache`. See `code-notes.md` § "site follow-up".

## Routes added by Phase 9a — role requests and timed roles (2026-08-27)

Built in `341757a` / `940927c` / `7605730` off `main` at `8b8f792`. Staff-gated
like every other router, ids are strings, refusals are sentences. **9b owns the
pages that read these, and owns adding them to `site/mock/contract.json`, the
mock server and `action_kinds`** — the checker walks only the routes the
contract already names, so it is green today without them.

### The queue — on the existing `/api/rolemenus` router

| Route | Body | Answers | Refuses |
|---|---|---|---|
| `GET /api/rolemenus/requests?status=` | — | a list, **pending first then newest first**: `id`, `menu_id`, `user_id`, `user_name`, `role_id`, `role_name`, `requested_at`, `status`, `decided_by_id`, `decided_by_name`, `decided_at`, `deny_reason` | `400 unknown_status` naming the five (`pending`, `approved`, `denied`, `withdrawn`, `granted_by_hand`) |
| `POST /api/rolemenus/requests/{id}/approve` | `{"days": 7}` — optional; omit for the menu's own number, `0` for no end date | `{"request": <row>, "message": "Approved — …"}` | `409 not_decided` when somebody already decided it, the member has left, or Discord refused the role · `400 bad_days` |
| `POST /api/rolemenus/requests/{id}/deny` | `{"reason": "not this month"}` — **required** | `{"request": <row>, "message": "Denied, …"}` | `400 no_reason` · `409 not_decided` |

Both decisions run the same `apply_request_decision` the Discord buttons run:
the role, the `role_grants` row, the member's DM and the edit of the card in
Discord all happen from a dashboard press too.

### Timed roles — the new `/api/roles` router (`black_bloc/api/tools/roles.py`)

| Route | Body | Answers | Refuses |
|---|---|---|---|
| `GET /api/roles/grants?user_id=&role_id=&limit=` | — | a list, **open first then newest first**: `id`, `user_id`, `user_name`, `role_id`, `role_name`, `source` (`menu`/`approval`/`staff`/`manual`), `granted_by_id`, `granted_by_name`, `granted_at`, `expires_at`, `removed_at`, `removed_reason`, `open` | — |
| `POST /api/roles/grants` | `{"user_id", "role_id", "days"?, "reason"?}` | the grant row; **adds the role too** (a role they already hold is not re-added) | `404 no_such_member` · `404 no_such_role` · `400 bad_days` · `409 role_refused` when Discord will not add it |
| `POST /api/roles/grants/{id}/extend` | `{"days": 7}` — **required** | the grant row with the new `expires_at` | `404 no_such_grant` · `409 already_ended` · `409 no_end_date` · `400 no_days` / `400 bad_days` |
| `DELETE /api/roles/grants/{id}` | — | the closed grant row, `removed_reason: "ended_by_staff"`; **takes the role off first** | `404 no_such_grant` · `409 already_ended` · `409 role_refused` |

### Menu payloads grew three fields

`POST /api/rolemenus` and `PUT /api/rolemenus/{name}` accept `approval` (bool),
`expires_days` (int, `0` = never) and `retry_days` (int), and every menu row
now carries them back. On PUT a field the page omits is **left alone**; sending
`expires_days: 0` is how a clock is cleared. `400 bad_approval` / `400 bad_days`
for a value in the wrong shape.

### New action kinds (for `action_kinds` when 9b adds them)

`web.role.approved`, `web.role.denied`, `web.role.granted`,
`web.role.extended`, `web.role.ended`.

## Routes added by Phase 10a — polls (2026-08-27)

> Built on branch `worktree-agent-aa83500e6aae1280f` from `main` @ `6e08223`;
> the API commit is `09d8654`. ⚠️ **Not in `main` yet.** The page that reads
> these is 10b — 10a ships the routes, the contract entries and the mock, and
> nothing on the site renders them. **Last verified: 2026-08-27** —
> `node site/mock/check.mjs` 14 pages / **68 routes** (61 before), all keys
> present; `tests/api/test_contract.py` green against the real routers.

### The new router (`black_bloc/api/tools/polls.py`)

All eight are staff-gated on the router (`staff_dependency`), every write also
takes `writer_dependency` and leaves a `web.poll.*` line through `note()`, and
every id leaves as a **string**.

```
GET  /api/polls?status=&page=&per_page=      newest first, paged, every state by default
GET  /api/polls/requests                     the polls waiting on Approve or Deny
POST /api/polls/requests/{id}/approve        posts the poll, DMs the creator
POST /api/polls/requests/{id}/deny           body {reason}; 400 without one
GET  /api/polls/{id}                         one poll + its options + its voters
POST /api/polls/{id}/end                     close early, write and post the result
POST /api/polls/{id}/cancel                  stop it, publish no result
GET  /api/polls/{id}/export.csv              text/csv — NOT in contract.json
```

⚠️ **There is deliberately no `POST /api/polls`.** Creating from the dashboard
needs a channel picker and the panel surface, which ship together in 10b; a
create form that silently refused anonymous polls would be worse than none. The
index says so in its `notes` array rather than leaving the page to guess.

⚠️ **`export.csv` is not in `contract.json`** because both halves of the
contract check parse every answer as JSON. It is covered by
`tests/api/tools/test_polls.py` and by hand against the mock.

### The poll row (what a page may read)

`id`, `question`, `kind`, `surface`, `status`, `results`, `multi`, `anonymous`,
`auto_thread`, `hours`, `creator_id`, `creator_name`, `channel_id`,
`message_id`, `thread_id`, `ping_role_id`, `opens_at`, `closes_at`,
`reminded_at`, `closed_at`, `archived_at`, `total_votes`, `decided_by_id`,
`decided_by_name`, `decided_at`, `deny_reason`, `created_at`, `options`,
`winner_position`, `votes_dropped`.

`options` is a list of `{position, label, votes}`; `winner_position` is `null`
on a tie and on a poll nobody has voted in. `votes_dropped` is non-zero only for
a poll archived while `poll_archive_drop_votes` was on.

The index answers `{polls, total, shown, page, per_page, notes}`; one poll
answers `{poll, votes}` where a vote row is
`{user_id, user_name, position, label, at}` and `votes` is always empty for an
anonymous poll. Both write routes answer `{poll, message}`.

### Refusals

| Status | When |
|---|---|
| 400 `unknown_status` | a `status=` filter naming something no poll can be |
| 400 `no_reason` | deny with no reason |
| 404 `no_such_poll` | no such poll, or one belonging to another guild |
| 409 `not_closeable` / `not_cancellable` / `not_waiting` | somebody got there first |
| 409 `test_mode` | the poll's channel is not the test channel — see below |

⚠️ **The test-mode refusal is CONDITIONAL, unlike every other guarded route.**
`http.end_poll` is not one of the three calls `guard.py` patches, so end, cancel
and approve ask `guard.allows_channel(poll.channel_id)` themselves; a poll
already in the test channel is *allowed*. Deny is never refused — it posts
nothing.

### New action kinds (added to `contract.json`'s `action_kinds`)

`web.poll.approved`, `web.poll.denied`, `web.poll.end`, `web.poll.cancel`.

### Settings keys the settings page gains

A new `poll` namespace: `poll_mode`, `poll_who_can_create`, `poll_review_mode`,
`poll_default_hours`, `poll_channel_id`, `poll_ping_role_id`,
`poll_reminder_minutes`, `poll_auto_thread`, `poll_archive_days`,
`poll_archive_drop_votes`. `namespace_of()` derives it from the prefix, so no
code changed in `settings_api.py`; the mock's `SETTING_SPECS` gained the same
ten rows.

## Routes added by Phase 10b — the create form and recurrences (2026-08-27)

> Built on branch `worktree-agent-a9f9dbcabf9636130` from `main` @ `3eb7e4f`
> (10a's tip); the API-and-page commit is `85d05da`. ⚠️ **Not in `main` yet.**
> **Last verified: 2026-08-27** — `node site/mock/check.mjs` **15 pages / 72
> routes** (14 / 68 before), all keys present; `tests/api/test_contract.py`
> green against the real routers; every route below exercised by hand against
> the mock from the page's own origin.

### Four new routes on the same router

```
POST   /api/polls                              the create form — same rules as /poll create
GET    /api/polls/recurrences                  the polls that repeat
POST   /api/polls/recurrences/{id}/pause       body {paused: bool}; false starts it again
DELETE /api/polls/recurrences/{id}             stops it repeating; opened polls untouched
```

⚠️ **`POST /api/polls` is the route 10a deliberately left out**, and the reason
it can exist now is the panel: with anonymity and hidden results buildable, a
create form no longer has to silently refuse half of what it offers. The index's
`notes` array, which used to carry the "arrives with the next update" line, is
now empty.

**It shares `poll_plan` with `/poll create`** (`cogs/community/polls.py:250`),
so the page cannot post a poll Discord's own command would refuse and the
refusal sentence is identical. Body:

| Field | Notes |
|---|---|
| `question` | required |
| `kind` | `single` (default) / `checkbox` / `yesno` / `rating` / `date` |
| `options` | a **list** or a `A \| B` string — both accepted; ignored for yes/no, rating and date |
| `hours` | default `poll_default_hours` |
| `anonymous`, `results` | `results` is `live` or `close`; either can force the panel |
| `channel_id` | falls back to `poll_channel_id`; **400 with neither** |
| `ping_role_id`, `auto_thread` | default to the settings keys |
| `start`, `slots`, `step`, `step_unit` | date polls only; `step_unit` is `days` or `hours` |

It answers `{poll, message, note}` — ⚠️ **`note` is the sentence saying which
surface was picked and why**, or `null` for a plain Discord poll. The page shows
its own predicted sentence while you type, but this is the one that is true.

A recurrence answers `{id, question, kind, surface, hours, anonymous, results,
creator_id, creator_name, channel_id, cadence, cadence_said, at, tz, next_at,
paused, options, created_at}`. `cadence` is the raw token (`daily`,
`weekly:sat`, `monthly:12`) and **`cadence_said` is the same sentence Discord
shows**, rendered server-side by `polls.py:describe_cadence` so the two cannot
drift. `paused` is exactly `next_at is null`.

Pause answers `{recurrence, message}`; delete answers `{recurrence_id, message}`.

⚠️ **There is no create-a-recurrence route.** Setting one up needs a cadence, a
weekday-or-day-of-month and a timezone, and `/poll recur create` already asks
for those with Discord's own choice pickers. The page points at it rather than
offering the worse of the two forms.

### Ordering matters on this router

`/recurrences` is declared **before** `/{poll_id}`, exactly as `/requests`
already is — FastAPI matches in declaration order, and the other way round
`GET /api/polls/recurrences` would be read as poll id "recurrences" and 422.

### New refusals

| Status | When |
|---|---|
| 400 `poll_refused` | anything `poll_plan` rejects: no question, under two options, a duplicate label, a bad length, an unreadable date, a kind no surface carries, over 25 options |
| 400 `no_channel` | no `channel_id` in the body and no `poll_channel_id` set |
| 404 `no_such_recurrence` | not a repeating poll, or one belonging to another guild |
| 409 `no_review_channel` | review is on and `staff_channel_id` points nowhere — the draft is cancelled |
| 409 `not_posted` | Discord would not take it; the draft is cancelled and the reason is named |
| 409 `unreadable_cadence` | resuming a recurrence whose cadence can no longer be read |
| 409 `test_mode` | the chosen channel is not the test channel |

### New action kinds (added to `contract.json`'s `action_kinds`)

`web.poll.created`, `web.poll.recur_paused`, `web.poll.recur_resumed`,
`web.poll.recur_deleted`.

### One more settings key

`poll_date_labels` (enum `plain` / `timestamp`, default `plain`) joins the ten
10a added, so the `poll` namespace is **eleven** keys. It decides how a date
poll writes its slots — see `code-notes.md` § *polls (10b)*, which records the
one real poll posted to measure the question it answers.

### The page

`site/public/polls.html` + `site/public/assets/page-polls.js`, the fifteenth
entry in `app.js:TABS` and in `shell.js:GROUPS` under **Community**, with an
open-poll count in the rail (`shell.js:pollTally`). Sections: Polls (the mode
switch) · Pending review · Open polls · Repeating · Closed (result bars + CSV
export, paged) · Archive (shut by default, D14) · Create a poll · Settings.

---

## Chat 2 (11a) — the `/api/chat` routes (2026-08-27)

> Added by 11a, commits `e508232` + `6a91b87`. The Chat **page** is 11b; these
> routes exist and are tested without it. All eight are staff-gated by the
> router's `staff_dependency`, take and return ids as **strings**, and refuse in
> words. Contract entries live in `site/mock/contract.json` and the mock answers
> all eight — `site/mock/check.mjs` is clean at **80 routes**.

| Method | Path | Answers |
|---|---|---|
| GET | `/api/chat/intents` | `{intents: [...], settings: [...], slots: [...], notes: []}` — every intent with its `lines` nested and its own `tokens` (the chips the page offers: `{names}`/`{links}`, `{title}`/`{when}`/`{channel}`, `{list}`, `{count}`, `{menus}`/`{roles}`, `{time}`, `{roles}`), plus the six chat-namespace settings rows in the shape `/api/settings` uses. Seeds the guild's defaults if it has none, so the page is never blank |
| POST | `/api/chat/intents` | `{intent, message}` — a new **custom** intent (`kind` is always `canned`); an optional `text` becomes its first line |
| PUT | `/api/chat/intents/{intent_id}` | `{intent, message}` — `name`, `triggers`, `enabled`, `sort`; a built-in refuses the name change only |
| DELETE | `/api/chat/intents/{intent_id}` | `{removed, intent_id, message}` — **custom only** |
| POST | `/api/chat/intents/{intent_id}/lines` | `{line, message}` — `text`, optional `slot` (`filled` / `empty` / `attendee`) and `enabled` |
| PUT | `/api/chat/lines/{line_id}` | `{line, message}` — `text`, `slot`, `enabled` |
| DELETE | `/api/chat/lines/{line_id}` | `{removed, line_id, message}` |
| POST | `/api/chat/try` | `{intent, kind, slot, line}` — a **dry run** through the real classifier and the real live data; nothing is sent and no action row is written |

### Refusals

| Status | When |
|---|---|
| 400 `chat_refused` | a name that is not `[a-z][a-z0-9_]*`, longer than 60 characters, or one of Black Bloc's own; no trigger phrases, a trigger over 60 characters, more than 40 of them; an empty line, a line over 500 characters, a slot that is not one of the three |
| 400 `no_text` | `POST /api/chat/try` with nothing to try |
| 404 `no_such_intent` | no such intent, or one belonging to another guild |
| 404 `no_such_line` | no such line, or one whose intent belongs to another guild |
| 409 `name_taken` | this guild already has an intent by that name |
| 409 `built_in` | deleting one of Black Bloc's own intents, or renaming one |

There is **no `409 test_mode`** anywhere in this router: nothing here talks to
Discord. `/api/chat/try` renders a reply and returns it; it never sends one.

### New action kinds (added to `contract.json`'s `action_kinds`)

`web.chat.intent_created`, `web.chat.intent_edited`, `web.chat.intent_deleted`,
`web.chat.line_added`, `web.chat.line_edited`, `web.chat.line_deleted`.

### Four more settings keys

`chat_ignore_channels` (channels, default `[]`), `chat_greeting_reaction`
(bool, default false), `chat_reply_in_threads` (bool, default **true**),
`chat_route_ping_staff` (bool, default false) join `chat_mode` and
`chat_cooldown_seconds`, so the `chat` namespace is **six** keys. All six are
returned on `GET /api/chat/intents` as well as by `/api/settings`, and all six
were added to `site/mock/server.mjs`, which had never carried any of them.

(12a made the `chat` namespace **seven** — `chat_log_level` lands there on its
own prefix, so the Chat page's `settings` block carries it too.)

---

## `GET /api/actions` — the Logs filters and the CSV export (12a, 2026-08-27)

Added by **12a** (commits `da020f6`, `a6f422b`) for the Logs page. The route
kept every parameter and every key it already had, so Overview, Health and the
old Audit page work unchanged.

### Parameters

| Name | Meaning |
|---|---|
| `limit` | **kept as an alias of `per_page`** — three existing pages send `?limit=`. `per_page` wins when both are given. |
| `per_page` | page size, clamped 1–200, default 50 |
| `page` | 1-based; a page past the end is `actions: []` with the real `total`, not a 404 |
| `details` | `1` to include the `details` blob (unchanged; `summary` is always there) |
| `kind` | a whole kind or a dotted prefix (unchanged) |
| `user_id` | either end of the action (unchanged) |
| `feature` | one of the twelve `logkinds.FEATURES`; anything else is a **400 with a sentence naming the twelve** |
| `q` | case-insensitive substring over kind, actor name, target name, reason and the details JSON |
| `since` / `until` | ISO; a bare `2026-08-27` as `until` means the **end** of that day |
| `important` | `1` for the lines that acted on a member or failed |

### Response

`{actions: [...], kinds: [...], limit, per_page, page, total, shown, notes}`

- Every row gains **`feature`**, **`important`** and **`summary`** (the reason,
  else the details flattened to `key=value`). Actor and target stay **flat**
  (`actor_id` / `actor_name` / `target_id` / `target_name`).
- **`kinds`** is the distinct kinds this guild has logged under the current
  `feature` — the page's chips, with no second request. ⚠️ It follows `feature`
  **alone**: paging past the end, or a `q` that matches nothing, must still
  leave the chips standing. Pinned by *the chips are what this guild logged, not
  the page it asked for*.
- `total` is what matched; `shown` is what this page returned.
- ⚠️ **The scan is capped at 5000 rows** (`actionlog.SCAN_LIMIT`), because
  importance and `q` are Python predicates rather than columns. When the cap is
  hit, `notes` says so in a sentence — the count is never quietly smaller than
  the truth without saying why.

### `GET /api/actions/export.csv`

Same filters, `text/csv`, `Content-Disposition: attachment;
filename="black-bloc-log.csv"`, columns `id, at, kind, feature, important,
actor_id, actor_name, target_id, target_name, reason, details`. It is
**deliberately NOT in `contract.json`** — `check.mjs` reads JSON shapes and this
one answers CSV, exactly as `/api/polls/{id}/export.csv` already is. Its
refusals are the list route's refusals (400 on a bad feature / date / id, 401
signed out, 503 with no guild or no database).

### Twelve more settings keys

`<feature>_log_level` for each of `logkinds.FEATURES`, enum
`off`/`important`/`all` (quietest first — the order the page's segment renders),
default `important`. ⚠️ **`mod_log_level` is in
`settings_api.NAMESPACE_OVERRIDE` → `automod`**, alongside `modlog_channel_id`
and `mod_dm_on_action`: the contract asserts `no_namespaces: [mod, modlog]`, and
the moderation settings already live under `automod`. The rest land on their own
prefix, so the registry's singular names are what the pages read —
`birthday_log_level`, `poll_log_level`, `rolemenu_log_level`.
## Requests (13a) — `/api/requests`

> Added 2026-08-27 by 13a (`27ec297`, contract/mock `415eb8c`). The dashboard
> page that reads them is **13b**. **Last verified: 2026-08-27** — `pytest -q`
> **2071 passed** and `node site/mock/check.mjs` clean at **88 routes**; nothing
> has been run against live Discord.

⚠️ **This is the first router on the site that is not staff-only end to end.**
`black_bloc/api/writes.py:member_dependency` is a new gate — signed in **and**
in the guild — and it is declared on exactly **three** routes. Every other route
in the whole API, this router's included, keeps `staff_dependency` /
`writer_dependency` / `reader_dependency` untouched.

| Method | Path | Gate |
|---|---|---|
| `GET` | `/api/requests?status=&assignee=&q=&page=` | staff (reader) |
| `POST` | `/api/requests` `{what, why, due_on?}` | **member** |
| `GET` | `/api/requests/mine?page=` | **member** |
| `POST` | `/api/requests/{id}/withdraw` | **member**, own row, pending only |
| `GET` | `/api/requests/{id}` | staff (reader) |
| `POST` | `/api/requests/{id}/approve` | staff (writer) |
| `POST` | `/api/requests/{id}/decline` `{reason}` | staff (writer) |
| `POST` | `/api/requests/{id}/status` `{status?, assignee_id?, priority?, notes?, reason?}` — `status` is one of `approved` `planned` `in_progress` `done` `declined` | staff (writer) |
| `POST` | `/api/requests/{id}/comments` `{text}` | staff (writer) |
| `GET` | `/api/requests/export.csv?status=&q=` | staff (reader) |

### The row every GET carries

```
{id, what, why, due_on, status, status_word, priority, notes,
 requester: {id, name, avatar}, assignee: {id, name, avatar} | null,
 comment_count, created_at, decided_by, decided_by_name, decided_at,
 decline_reason, done_at}
```

Ids are **strings**. `assignee` is `null` when nobody owns it. `status` is one
of `pending` `approved` `planned` `in_progress` `done` `declined` `withdrawn`;
`status_word` is the same thing in words, so the page never has to hold its own
copy of the vocabulary. A comment is
`{id, request_id, author: {id, name, avatar}, text, at}`.

`GET /api/requests` answers `{requests, total, page, pages, per_page, pending}`
— `pending` is the sidebar badge, and it counts the whole guild, not the page.
`GET /api/requests/mine` answers the same object without `pending`.
`GET /api/requests/{id}` answers `{request, comments}`. Every write answers
`{request, message}` — or `{comment, message}` for a comment.

**Pending first, then newest.** `ORDER BY (status <> 'pending'), id DESC`, in
SQL rather than in Python, so a page is a `LIMIT`/`OFFSET` and not a slice of
everything. 20 a page.

**Filters.** `status=` takes a comma list of the seven states. `assignee=` takes
an id, or the word **`none`** for the board's Unassigned column. `q=` matches
`what`, `why`, `notes` **and the requester's name** — the name is resolved
against the gateway's member cache in Python and OR-ed in as `user_id IN (…)`,
because a Discord display name is not a column.

⚠️ **`due_on` is a plain `YYYY-MM-DD` string on the wire in both directions** —
row and POST body — never an ISO instant. It becomes `<t:…:D>` only where it is
rendered (the DMs and `/request list`), from **local midnight in the server's
zone**.

⚠️ **`POST /api/requests` is NOT refused under `TEST_MODE`.** It writes a row;
the only thing that reaches a channel is the optional notice line, and that asks
the guard itself and skips.

### `/api/auth/me` now says `member`

`{user, staff, member, state, guild, message}`. `state` is unchanged
(`staff` / `not_staff` / `staff_unknown`) so nothing that already reads it
breaks; `member` is new, and `message` for a signed-in **member** who is not
staff is now `auth.MEMBER_NOT_STAFF` — it says the rest of the dashboard is
staff-only but they can still file a request — instead of the flat `NOT_STAFF`.
A signed-in person who is **not** in the guild still gets `NOT_STAFF`.

### Refusals

| Status | When |
|---|---|
| 400 `request_refused` | an empty What or Why, a due date that is not `YYYY-MM-DD`, a priority outside 0–5, a `status` that is not one of the five staff states, a `status=` filter naming a state that does not exist |
| 400 `no_reason` | declining without a line the person is sent |
| 400 `no_text` | a comment with nothing in it |
| 400 `no_such_member` | an `assignee_id` Discord does not show in this guild |
| 400 `nothing_to_save` | `POST …/status` with no status and no field |
| 403 `not_a_member` | signed in, but not in the guild (the member gate) |
| 403 `staff_only` | `request_who_can_file = staff` and the caller is not |
| 403 `not_yours` | withdrawing somebody else's row |
| 404 `no_such_request` | no such request, or one belonging to another guild |
| 409 `requests_off` | `request_mode = off` |
| 409 `not_pending` | withdrawing a row that has already been decided |
| 409 `not_decided` | moving a row to the state it is already in |
| 429 `slow_down` | ten member writes a minute per person (`writes.MEMBER_RATE`) |
| 503 `member_unknown` | the guild cannot be consulted, so membership is unknown |

There is **no `409 test_mode`** in this router. The one thing that reaches a
public channel is the notice line, and `cogs/community/requests.py:notify` asks
the guard itself and skips rather than raising — a request is filed either way.

### New action kinds (added to `contract.json`'s `action_kinds`)

`web.request.filed`, `web.request.approved`, `web.request.declined`,
`web.request.planned`, `web.request.in_progress`, `web.request.done`,
`web.request.withdrawn`, `web.request.updated`, `web.request.comment`.
The cog's own kinds are the same words without the `web.` — plus
`request.auto_approved`, `request.dm_failed` and `request.notify_failed`.

### Five more settings keys

`request_mode` (enum off/on, default **on**), `request_who_can_file` (enum
everyone/staff, default **everyone**), `request_auto_approve_staff` (bool,
default **true**), `request_notify_channel_id` (channel, the test channel while
`TEST_MODE` is on and nothing once it is off), `request_dm_on_decision` (bool,
default **true**). They land on their own `request` namespace in
`/api/settings`. `request_mode` is in `command_visibility.HIDDEN_WHEN_OFF`, so
turning it off takes `/request` out of the tree as well.

### Not in `contract.json`

`GET /api/requests/export.csv` — it answers CSV, not JSON, exactly as
`/api/polls/{id}/export.csv` and `/api/actions/export.csv` already are.
`POST /api/requests/{id}/withdraw` — it only ever answers 200 for the person who
filed the row, which one fixture session cannot exercise both ways; it is
covered in `tests/api/tools/test_requests.py` instead.
