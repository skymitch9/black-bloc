# Temporary roles — the role menu becomes the permanent staff control; a role ends on a date or with a marathon (request #17)

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-11-13 09:5x Phoenix)** — dispatches to
> Opus as branch `temp-roles-menu` once the before-dispatch usage read exists. **Last verified: 2026-11-13 09:4x** against `main`
> `8556fcc8` by reading the code, and against the live site through the operator token (request #17; `GET /api/marathons`).
> ⚠️ NOT verified: anything in Discord; the bot was not run; no browser; the guild's current role list (the role names below are
> from the 2026-08-26 scan and are examples, never a fixed list).

## 1. The ask, and the decisions

Request #17 (*[Nosey] Champrul*, 2026-11-13 16:16Z, `open`): *"deactivate BtB speciifc roles — Runners, commentators, hosts,
donations, tech checkers, social media assists, moderators. Tentatively would need to deactivate those on February 28th (date may
change)"*. BtB = Back to Black (2027 edition; not a tracked marathon as of 09:1x).

Owner, 2026-11-13, in order:
1. *"we can assign roles that way. Lets rework the role menu or make a new feature for assigning temporary marathon related roles."*
2. *"make this reusable and have it match a marathons end date. so all roles given will be taken on a date matching the marathon,
   with a buffer to maybe add 1 day or so to the end for clean up"*
3. Q2 → **(a) rework the role menu.**
4. Q3, verbatim: *"we dont need a permanent role manu anymore because we have the roles selectable in discord. this temporary role
   menu will be permanent as a staff control to select people and give them roles and also to set end dates for roles. when that
   end date or marathon expiry happens anyone with that role will lose it. the menu is perma the roles are temporary"*

So the model is: **a menu is a permanent staff grouping of roles; the menu carries ONE end (a typed date, or a tracked marathon's
end plus a buffer); when the end comes, every member wearing any of the menu's roles loses them — not only bot-recorded grants.**
Member self-pick (posted panels, approval requests, `rolemenu_mode`) is retired: Discord onboarding owns self-serve roles.

## 2. Measured (main `8556fcc8`)

| Fact | Where |
|---|---|
| `role_menus` has `mode`, `message_id`, `channel_id`, `approval`, `expires_days`, `retry_days`; no end of its own | `storage/db.py:63-76` |
| A grant's expiry is per grant, in DAYS (`expires_days_of(menu)` → `grants.expires_at(days)`) | `cogs/community/role_menus.py:377`, `rolegrants.py:114` |
| The hourly `_expiry_loop` removes DUE GRANTS only (`run_due_grants` → `_expire`), one DM per grant; `reconcile_records` never touches members | `role_menus.py:3099-3160` |
| A by-hand role ADD is NOT recorded as a grant; only a pending request gets settled. Removals DO end grants | `role_menus.py:3168-3215` (`_added_by_hand`) |
| Staff hand-out (`Hand roles out…` ▸ `Give them roles…`) writes grants with the menu's `expires_days` | `role_menus.py:1340-1356` |
| `change_roles(bot, member, guild, add_set, remove_set, reason)` refuses roles above the bot / managed / no permission (`CANNOT_HAND_OUT`, `CANNOT_EDIT_THEIRS`) | `role_menus.py:1745` |
| A marathon's span is written after every fetch: `starts, ends = mt.span(runs)` → `update_marathon(... ends_at=...)` | `cogs/content/marathon.py:2164-2169` |
| `marathons.ends_at` exists; live list 09:1x: ids 2, 3, 5, 22, 23 — no Back to Black 2027 | `storage/db.py:1065`, `GET /api/marathons` |
| Panel root moves: New menu · Seed the defaults · Grants… · Logs · Refresh · mode on/off; a menu card: Add a role… · Words… · Rules… · Post/Move… · Take it down · Hand roles out… · Delete it | `rolemenus.py:150-260` |
| API: `GET/POST /api/rolemenus`, `/seed`, `/requests` (+approve/deny), `PUT/DELETE /{name}`, `/{name}/post`, `/{name}/assign`, `/{name}/unpost` | `api/tools/rolemenus.py:323-529` |
| Site: `rolemenus.html` + `page-rolemenus.js` — menus editor, *Requests* section (`:404`), *Timed roles* section (`:592`); `members.html` chips read `roles[].expires_at` | `site/public/assets/page-rolemenus.js` |
| Retiring a settings key = the `golive_end_*_RETIRED` pattern (`settings_store.py:106`, the `retired` set `:12273`) and `sticky_mode` in v242 (`DONE.md`) | `settings_store.py` |

## 3. Design

### 3.1 Data — the end lives on the menu

`role_menus` gains (additive migration, `SCHEMA_VERSION` +1):

| Column | Meaning |
|---|---|
| `ends_source` TEXT | `none` (no end yet) · `date` · `marathon` |
| `ends_marathon_id` INTEGER | the `marathons.id` when `ends_source = marathon`; `NULL` otherwise |
| `buffer_days` INTEGER | the clean-up buffer added to the marathon's `ends_at`; `NULL` = the guild default key |
| `ends_at` TEXT | the COMPUTED moment everyone loses the roles: the typed date, or `marathon.ends_at + buffer`; `NULL` when `none` |
| `ended_at` TEXT | set when the end pass has run; cleared when staff set a new end (the menu is reused next year) |

Rules:
- `ends_at` is recomputed in ONE helper (`rolemenus.ends_at_of(menu, marathon, default_buffer)`) called from: staff setting the
  end, the marathon span write (hook beside `cogs/content/marathon.py:2164-2169`: after `update_marathon`, re-stamp every menu
  bound to that marathon whose computed end changed → log `role_menu.end_moved` `{menu, from, to}` + the staff notice §3.4), and
  the marathon's archive/remove (`marathon_stale`, `DELETE /api/marathons/{id}`): the menu keeps its last computed `ends_at`,
  flips to `ends_source = date`, logs `role_menu.end_unbound` and notices staff. A marathon with no `ends_at` yet (Halo Fest,
  AGDQ 2027 today) binds fine: `ends_at` stays `NULL` until the schedule gives one; the card says *end not known yet*.
- A menu's end also stamps `role_grants.expires_at` for every OPEN grant on its roles (so the Grants… audit and the Members chips
  read the same date, one source) — but **removal is by ROLE, not by grant** (§3.3).
- Per-grant day counts (`Give somebody a role…` ▸ *How long for…*) stay for ad-hoc one-person grants; a grant on a menu role is
  clamped to the menu's end when the menu has one (`min(grant end, menu end)`).

### 3.2 The staff control — `/rolemenu`, permanent

Renders regardless of `rolemenu_mode` (the key is retired, §3.5). No blurbs; labels carry the meaning.

**Root panel** — embed lists each menu as one line: *Back to Black 2027 · 7 roles · 23 wearing · ends <t:…:D> (Back to Black
2027 + 1 d)* / *… · no end set*. Buttons: **New menu** · **Grants…** (unchanged audit) · **Logs** · **Refresh**. Gone: *Seed the
defaults* (the seeds were self-pick menus), the mode on/off button, *Waiting on staff (N)…*.

**Menu card** — embed: the roles (with wearing counts, read live from the guild), the end line, who set it and when, the last pass
(*ended 2026-03-01 · 23 people · 0 failures*). Buttons:
- **Add a role…** (existing RoleSelect; a role is refused in words when `change_roles` could not remove it — the refusal is the one
  that matters now, because the end pass must be able to strip it) · **Remove a role…** (existing).
- **Hand roles out…** → existing *Give them roles…* / *Take roles back…* (UserSelect + the menu's roles). Grants are written with
  `until = menu ends_at`.
- **Set the end…** (new, primary) → sub-panel: a **marathon select** (every non-archived marathon, upcoming first, labelled *name ·
  ends <date>* or *name · end not known yet*; 25-capped with `capped_placeholder`) · **Type a date…** (modal: `YYYY-MM-DD`, a time
  optional, guild-local; refused in words when in the past) · **Buffer…** (modal, whole days, 0 allowed; blank = default) ·
  **No end** (clears; confirm). Picking a marathon or a date re-stamps `ends_at`, clears `ended_at`, logs `role_menu.end_set`.
- **End it now** (danger) → confirm names the count (*Take 7 roles off 23 people now?*) → runs the end pass immediately (§3.3).
- **Words…** (title/description — still the card's words) · **Delete it** (existing confirm; refused in words while the menu has
  an end in the future and people wearing its roles — *End it now first*).
- Gone from the card: *Rules…* (mode / approval / retry days), *Post… / Move… / Take it down*.

### 3.3 The end pass — everyone wearing the role loses it

Runs inside the existing `_expiry_loop` tick (hourly) as a second step, `run_due_menus()`, and on **End it now**:

1. Menus with `ends_at <= now` and `ended_at IS NULL`.
2. For each: the menu's role ids → every `guild.member` wearing ANY of them (gateway cache; `chunk` if the guild is not chunked).
3. **One `change_roles` per member** removing all of that menu's roles they wear (one API call per member; discord.py waits on
   429s). On a refusal/failure: log `role_menu.end_failed` `{menu, user, roles}` and continue — the member stays due; the next tick
   retries because `ended_at` is only stamped once a pass finishes with zero failures OR `ROLE_MENU_END_RETRIES` (3) passes have run
   (then `ended_at` is stamped, `end_failures` recorded, and the staff notice lists who still wears what).
4. Close every open grant on those roles for those members (`end_grant(..., EXPIRED)`), including grants the bot never knew (a
   by-hand holder has no row — nothing to close; the role still comes off).
5. **One DM per member** listing every role that ended (`rolemenu_ended_dm` template: *{roles} on {guild} ended with {what}* — `{what}`
   = the marathon's name or the date), replacing the per-grant `DM_EXPIRED` for this pass. Members hear nothing before this.
6. Log `role_menu.ended` `{menu, roles, members, failures}`; staff notice (§3.4); the menu card re-renders.

`reconcile_records` is unchanged and still never touches members.

### 3.4 Notices — staff hear about moves, members hear at the end

Posted to `rolemenu_approval_channel_id` (default = `staff_channel_id`; its label becomes *Where role notices post*), with the
`rolemenu_approver_role_id` ping if set:
- `rolemenu_end_moved_notice` (bool, **default on**): *Back to Black 2027's end moved: roles now end <t:…:F> (was <t:…:F>)* — on
  a marathon re-date and on unbinding.
- `rolemenu_ended_notice` (bool, default on): *Back to Black 2027 ended — 7 roles taken off 23 people. 0 failures.* / with the
  failures listed by name and role.
Every sentence is a settings key (rule: every word editable). Keys: `rolemenu_end_buffer_days` (int, default **1**),
`rolemenu_end_moved_notice`, `rolemenu_end_moved_text`, `rolemenu_ended_notice`, `rolemenu_ended_text`, `rolemenu_ended_dm`,
`rolemenu_end_not_known_text`, the Set-the-end labels/titles/placeholders, the refusal sentences. Registry + mock row + label each.

### 3.5 Retiring member self-pick

Code and data stay (a rehearsal or a reversal costs nothing); nothing renders or answers:
- `rolemenu_mode`, `rolemenu_off_confirm_*`, per-menu `mode` / `approval` / `retry_days`, `role_menus.message_id/channel_id`:
  retired the `golive_end_*_RETIRED` way — hidden from Settings and the editor, kept in the DB.
- Posted panels: on boot, `_register_panels` stops re-registering menu panels; an existing posted panel's select answers
  `ROLE_MENUS_RETIRED` (one new key: *Roles are picked in Discord's own Channels & Roles now.*). Nothing is deleted from channels
  by the build — the owner takes posted panels down by hand or they are left; say which in the report.
- API: `/{name}/post`, `/{name}/unpost`, `/requests*`, `/seed` answer `410` in words (`rolemenu_retired`, three-part refusal per
  the global rule); the site stops calling them. `PUT /{name}` gains `ends_source`, `ends_marathon_id`, `ends_at` (date source),
  `buffer_days`; `POST /{name}/end-now`; `GET` rows gain `ends_*`, `ended_at`, `wearing` (count), `end_label`.
- Open `role_requests` rows: left as they are (decided collapsed on nothing); the request cards in the approval channel are edited
  once to the retired sentence by a one-off boot sweep logged `role_menu.requests_retired`.

### 3.6 Site

- **`rolemenus.html`** (owns roles and grants — one fact, one home): the menu editor loses mode/approval/retry/channel/Post and gains
  **End**: a marathon select (same list as the panel, `#name · ends date`), a date input, a buffer field, *No end*; each menu row
  shows *ends <date> · N wearing*, *End it now* with the count confirm. The *Requests* section is removed; *Timed roles* stays.
  Deep link for the owner's review: `https://blackbloc.heygabi.ai/rolemenus.html`.
- **Marathon drawer** (Events page): one read-only line on the Event card — *Roles ending with this marathon: Back to Black 2027
  (7 roles · 23 people)* → links to `rolemenus.html#<menu>`. Nothing editable there.
- **`members.html`** chips: a role on a menu with an end shows *· ends <date>* even with no grant row (the Members API's `expiries`
  map merges menu ends by role id).
- Mock: rows + the contract check (`node site/mock/check.mjs`) for every new/changed route and key.

### 3.7 Logs and health

New kinds: `role_menu.end_set`, `role_menu.end_moved`, `role_menu.end_unbound`, `role_menu.ended`, `role_menu.end_failed`,
`role_menu.requests_retired`. The Health tab's expiry loop line gains *menus due / ended / failures*.

## 4. Tests (mirror the package)

`tests/test_rolemenus.py` (ends_at_of: date, marathon + buffer, default buffer, no end yet, past refusal; the move detection),
`tests/test_rolegrants.py` (clamp to menu end), `tests/cogs/community/test_role_menus.py` (the end pass: every wearer loses the
roles incl. a by-hand holder with no grant; one DM per member listing all roles; a refusal is logged and retried, `ended_at` stamped
after the retry cap; End it now confirm names the count; Set the end sub-panel; retired moves do not render; a posted panel's
select answers the retired sentence), `tests/cogs/content/test_marathon.py` (span write re-stamps bound menus and posts the notice;
archive unbinds), `tests/api/tools/test_rolemenus.py` (new fields, 410s in words, end-now), `tests/api/tools/test_members.py`
(chip end from a menu), site node tests + `check.mjs`.

## 5. Rollout

- Branch `temp-roles-menu` off `main`. **Two dispatches**, each ≤ ~250k: (1) storage + `rolemenus.py` + cog + API + mock contract
  + tests; (2) site (`page-rolemenus.js`, marathon drawer line, members chips) + node tests, after (1) merges. Both briefs carry:
  `docs/info/review-checklist.md` (47 items), code-notes re-key, no blurbs, every word a key, commit at clean boundaries, no
  `git stash`, directory deploys from a worktree of HEAD only.
- Merge, gate (`pytest -q -n 16 -rfE`, `ruff`, `check.mjs`), deploy per `access/deploy.md` with the previous release noted in
  `deploys.log`; rollback if boot or `/rolemenu` fails.
- **Live verification (the owner, by eye):** `/rolemenu` ▸ New menu *Back to Black 2027* ▸ Add the volunteer roles ▸ Set the end…
  ▸ Type a date 2027-02-28 (the marathon is not tracked yet) with buffer 1 → the card reads *ends 2027-03-01*. When Back to Black
  2027 is added as a marathon, Set the end… ▸ pick it. Nothing is removed from anyone until that date.
- Request #17 stays `open` → staff press *in progress* at dispatch; *ready to check* only on the owner's sign-off.

## 6. Deviations the builder may take (record each at the foot of this note)

None pre-approved beyond the design. Anything that changes a persisted key, a decision default or a surface's owner comes back to
the conductor first.
