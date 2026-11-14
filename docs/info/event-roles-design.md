# Temporary roles — the role menu becomes the permanent staff control; a role ends on a date or with a marathon (request #17)

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **1a LIVE v271; 🔨 1b + 2 BUILT on branch
> `temp-roles-menu`, not merged** (2026-11-13; 1a's deviations and interface at §6.1–6.2, what the site reads at §6.3, 1b's at
> §6.4, dispatch 2's at §6.5). 📐 Design by Fable, 2026-11-13 09:5x Phoenix. **Last verified: 2026-11-13 09:4x** against `main`
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
- Per-grant day counts (`Give somebody a role…` ▸ *How long for…*) stay for ad-hoc one-person grants on roles that sit on NO menu;
  a grant on a menu role is clamped to the menu's end when the menu has one (`min(grant end, menu end)`), and **Push it back…** on a
  grant whose role is on a menu with an end is refused in words (*{role} ends with {menu} on {date} — change the menu's end instead*).
- Per-menu `expires_days` is dead (Hand roles out… writes the menu end): retired the same way as `mode` / `approval` (§3.5), kept in the DB.
- `_added_by_hand` is **unchanged** — a by-hand holder gets NO grant row. Removal is by role (§3.3), so no row is needed.
- **The Grants… audit lists WEARERS, not rows, for a role on a menu with an end:** every member wearing the role (live from the guild)
  with the menu's end, soonest first; grant rows are listed only for roles on no menu. The menu card's *N wearing* and the audit then
  answer *who loses this role* with the same number — two surfaces, one source.
- A typed date with no time ends at **23:59 guild-local** in `default_timezone` (Champrul's *"on February 28th"* means after the 28th);
  the card shows the resolved moment as `<t:…:F>`.

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
   429s). `change_roles` already calls `grants.remember_change` (`role_menus.py:709-710`), so `on_member_update` sees the removals
   as ours and does not log 23 × 7 `role.changed_by_hand` rows — the pass MUST go through `change_roles`, never `member.remove_roles`. On a refusal/failure: log `role_menu.end_failed` `{menu, user, roles}` and continue — the member stays due; the next tick
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
- Open `role_requests` rows: **none exist** (live 09:5x: `GET /api/rolemenus/requests` → 0), and **no menu is posted** (all 7 live
  menus have `message_id = null`), so the retired-sentence paths above are safety nets, not a sweep; drop the boot sweep and
  `role_menu.requests_retired`. The 7 live menus are the Phase 9 seeds (`event-alerts`, `interests`, `mentoring`, `notifications`,
  `playstyle`, …), all self-pick groupings with no end: the build leaves them untouched (they read *no end set*); deleting them is
  the owner's call via **Delete it**, named in the report.

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

New kinds: `role_menu.end_set`, `role_menu.end_moved`, `role_menu.end_unbound`, `role_menu.ended`, `role_menu.end_failed`. The Health tab's expiry loop line gains *menus due / ended / failures*.

## 4. Tests (mirror the package)

`tests/test_rolemenus.py` (ends_at_of: date, marathon + buffer, default buffer, no end yet, past refusal; the move detection),
`tests/test_rolegrants.py` (clamp to menu end), `tests/cogs/community/test_role_menus.py` (the end pass: every wearer loses the
roles incl. a by-hand holder with no grant; one DM per member listing all roles; a refusal is logged and retried, `ended_at` stamped
after the retry cap; End it now confirm names the count; Set the end sub-panel; retired moves do not render; a posted panel's
select answers the retired sentence), `tests/cogs/content/test_marathon.py` (span write re-stamps bound menus and posts the notice;
archive unbinds), `tests/api/tools/test_rolemenus.py` (new fields, 410s in words, end-now), `tests/api/tools/test_members.py`
(chip end from a menu), site node tests + `check.mjs`.

## 5. Rollout

- Branch `temp-roles-menu` off `main`. **Three dispatches in sequence** (the calibration table puts one subsystem at ~279k and a
  multi-layer build at ~474k): **1a** storage + `rolemenus.py` helpers (`ends_at_of`, the wearers audit) + the end pass + the
  marathon hook + their tests; **1b** the panel sub-panels (Set the end…, End it now), API fields and 410s, retirement, mock contract +
  tests; **2** site (`page-rolemenus.js`, marathon drawer line, members chips) + node tests. Each commits at clean boundaries and
  lands fewer things completely over one thing half-built. Both briefs carry:
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

### 6.1 What 1a built, and every deviation or decision it took (2026-11-13, branch `temp-roles-menu`)

Code notes: [`code-notes.md`](code-notes.md) ▸ *Temporary roles, core*.

**Deviations from the text above**

1. **Accessors live in `cogs/community/role_menus.py`, not `storage/db.py`.** `db.py` holds no accessors at all; every
   `role_menus` query already sits beside `get_menu` in the cog module, so the new ones (`menus_still_to_end`, `menus_bound_to`,
   `store_menu_end`, `restamp_menu_end`, `unbind_menu_end`, `record_end_pass`, `marathon_row`) do too.
2. **The end pass runs FIRST in the tick, not second** (`run_due_menus` → `run_due_grants` → `reconcile_records`), and the grant
   path skips a grant whose role is on a DUE, unfinished menu. Otherwise grants stamped with the menu's end come off one by one
   with `DM_EXPIRED` (and `cog_load` runs the grant path on its own), breaking §3.3 step 5's one DM per member.
3. **Six columns beyond §3.1's five:** `end_passes` (the retry counter), `end_members` (people the roles came off, summed over
   every pass — the ended notice and the card's *ended … · 23 people*), `end_failures` (JSON leftovers at the cap), `ends_told_at`
   (see 6 below) and `ends_set_by`/`ends_set_at` (the card's *who set it and when*, so 1b needs no second migration).
   `role_menu.end_failed` per member carries `{menu, menu_id, user, roles}` with `roles` = the ones still on; `role_menu.ended`
   carries `roles` (the menu's), `members` (the running total), `this_pass`, `failures`, `left`, `passes`.
4. **`ROLE_MENU_END_RETRIES` is a constant (3), not a key** — the brief named it so. ⚠️ It is a decided number; if staff should be
   able to change it, it becomes a key (checklist 33). Question for the conductor.
5. **Two keys beyond §3.4:** `rolemenu_end_unbound_text` (the unbinding sentence — "every word a key") and
   `rolemenu_end_failure_line` (one line per member still wearing a role, under the ended notice). `rolemenu_end_not_known_text`
   (*end not known yet*) was added now because the moved notice says it when a marathon first gets dates.

**Decisions 1a had to make — each named for the conductor**

6. ⚠️ **NEW DECISION DEFAULT: `rolemenu_end_moved_minutes` = 60** (int 0–10080). `mt.span` moves on every live read of a schedule
   that writes actuals (checklist 41/42), so "notice when the end changed" would ping staff every minute during a live marathon.
   The end ALWAYS follows the marathon (restamped silently); `role_menu.end_moved` + the notice fire only when it has moved ≥ 60
   min from the last end staff were TOLD (`ends_told_at`), so drift cannot add up unseen. 0 = every move.
7. **Guard:** with `bot.guard` set (TEST_MODE) the pass logs `role_menu.would_end` (wearers listed) and does nothing, counting
   no pass — the `handed_roles.take_back` precedent. ⚠️ The existing `_expire` grant path has NO guard check; 1a did not change it.
   The pass is NOT gated on `rolemenu_mode` (or on anything else): `bot.guard` is the only brake, and it is `None` on Fly.
8. **End it now** (`end_menu_now`) writes the end as `date` = now (unbinding a marathon) and then runs the pass, so a pass that
   leaves failures is retried by the hourly tick like any other end. Under `bot.guard` it logs `would_end` and writes NOTHING, so
   a rehearsal cannot arm a menu that strips everyone at the first tick after the guard lifts.
9. **Stamping OVERWRITES** an open grant's `expires_at` with the soonest unfinished menu end of its role — including a grant that
   had a shorter ad-hoc end from before. A min() would leave an old stamp behind when an end moves later, and the grant path would
   then take the role off on the old date. Clearing an end (`source="none"`) nulls only the stamp the menu had put there. The
   shared paths `put_option` (stamps), `drop_option` and `drop_menu` (take the menu's stamp back) re-stamp too, so a role that
   leaves a menu is not stripped on the menu's date by the grant path.
10. **An unreadable `ends_at` is never due** (no role removed on a garbled date); it blocks nothing else.
11. **An empty or short member cache is not a pass:** chunk first; still short of `member_count` → `role_menu.end_failed`
    `members_not_loaded`, nothing stamped, retried next tick.
12. **Grants closed by the pass:** every open grant on the menu's roles, members who left included; only members still wearing
    a role after a failure keep theirs. ⚠️ After the 3-pass cap those leftover grants stay open with a past `expires_at`, so the
    existing grant path keeps retrying them hourly (`role.expire_failed`) as it does any refused removal today.
13. **A marathon re-dated after its menu ENDED does not move the menu** — the roles already came off; reuse is staff setting a new
    end. A menu bound to a marathon that never got an end unbinds to `none`, not to a date with no moment.
14. **The marathon hooks swallow their own faults** (logged), so a role-menu bug never stops a schedule read or an archive.
15. **Notices ship ON** as §3.4 says (they post to the staff/approval channel, not to members). Nothing posts or is removed until a
    menu has an end, and 1a has no door that sets one — 1b does.
16. **Log kinds:** `role_menu.end_set`, `.end_moved`, `.end_unbound` added to `IMPORTANT`; `.ended` and `.end_failed`,
    `.notice_failed` are important by suffix; `.would_end` is routine by the shadow rule.

17. **The per-menu locks hang on the bot** (`end_lock(bot, menu_id)`, like the role ledger), not on the module: discord.py's
    `load_extension` executes the cog module afresh, so the marathon cog's import and the loaded cog could hold two copies.

**Open questions for the conductor (built as described; not decided by 1a)**

- ✅ **Answered by the conductor for 1b (2026-11-13): held for staff** — see §6.4 item 1. ~~**An end that moves EARLIER.**~~ One schedule read that pulls `marathons.ends_at` earlier (a truncated list, a corrected actual,
  checklist 42) can make a bound menu due at the next tick, and the pass is irreversible. Should a move earlier wait for a second
  read, or for staff, before the menu becomes due? Today it follows at once (with the notice if ≥ the floor).
- **Restore.** Restoring an archived marathon does not rebind the menu that was unbound from it; staff pick it again.
- **`ROLE_MENU_END_RETRIES`** constant vs key (item 4).

**MUST for 1b:** `api/tools/rolemenus.py` `sync_options` writes options with `add_option`/`remove_option` directly, not through
`put_option`/`drop_option`, so it does not re-stamp grants — 1b must call `stamp_grants(db, guild_id, changed_role_ids,
was=(menu["ends_at"],))` there (or route it through the shared functions). `pings.py` edits its own events menu the same way;
it only matters if that menu is ever given an end.

**NOT built in 1a (1b's):** the clamp is a helper only (`rolegrants.clamped`) — `grant_role` / `staff_assign` / *Push it back…*
do not call it yet; the Health line (*menus due / ended / failures*); every panel, API and site change; the refusal sentences for
Set the end… (past date, unknown marathon).

### 6.2 The interface 1b calls (all in `black_bloc/cogs/community/role_menus.py` unless named)

| Need | Call |
|---|---|
| Set / change / clear the end | `await set_menu_end(bot, guild, actor, menu, *, source, marathon_id=None, ends_at=None, buffer_days=None, via=VIA_DISCORD) -> str \| None` — `source` in `rolemenus.END_SOURCES` (`"none"`, `"date"`, `"marathon"`); `ends_at` a `datetime` or ISO string (date source); raises `ValueError` for an unknown source or a marathon not in this guild (1b refuses in words BEFORE calling). Clears `ended_at` and the pass counter, stamps grants, logs `role_menu.end_set` via `kind_via` (a route passes `via=VIA_WEBSITE` and never `note()`s, checklist 34). Returns the computed end. |
| Resolve a typed date | `rolemenus.typed_end(text, store.get(guild.id, "default_timezone")) -> datetime \| None` (date alone = 23:59 local). |
| End it now | `await end_menu_now(bot, guild, actor, menu, *, via=VIA_DISCORD) -> dict \| None` — the pass's details (`members`, `failures`, `left`, `passes`, `ended`), or None when guarded / cache short. |
| Run the pass for one due menu | `await end_menu(bot, guild, menu_id, *, actor=None, via=VIA_DISCORD)` |
| Re-stamp grants by hand | `await stamp_grants(db, guild_id, role_ids, *, was=())` |
| Who wears the menu's roles (the audit, the card's count, the confirm's count) | `rolemenus.wearers(members, role_ids) -> [(member, [role_ids])]`, with `await members_of(guild)` (None = cache short) and `await menu_role_ids(db, menu_id)` |
| Clamp a new grant on a menu role | `rolegrants.clamped(until, menu_end)` |
| The computed end of a menu | `rolemenus.ends_at_of(menu, marathon_row_or_None, store.get(guild.id, "rolemenu_end_buffer_days"))` |
| Is it due | `rolemenus.is_due(menu, datetime.now(UTC))` |
| Render a sentence key | `rolemenus.said(store, guild_id, key, **fields)` (falls back to the shipped default, checklist 17) |

### 6.3 For the dispatch-2 (site) builder: every route and field the Role menus page uses

All routes are staff-only (session + staff role), as before. Every refusal is `{"error": code, "message": sentence}`; show the
sentence, never the status. Times are UTC ISO strings; `end_label` is already in words (guild-local, no `<t:>` tokens).

**`GET /api/rolemenus`** — one row per menu:

```json
{
  "name": "btb-2027", "title": "Back to Black 2027", "description": null,
  "options": [{"role_id": "1285361896383320074", "label": "Runner", "emoji": null, "position": 0}],
  "ends_source": "marathon", "ends_marathon_id": "24", "buffer_days": null, "buffer_default": 1,
  "ends_at": "2027-03-01T05:00:00+00:00", "ended_at": null, "ends_held_at": null,
  "ends_set_by": "1234", "ends_set_at": "2026-11-13T20:00:00+00:00",
  "wearing": 23, "end_label": "ends 2027-02-28 22:00 (Back to Black 2027 + 1 d)",
  "last_pass": {"passes": 0, "members": 0, "failures": 0, "ended_at": null},
  "mode": "staff", "channel_id": null, "message_id": null, "approval": false, "expires_days": null, "retry_days": 7
}
```

- `ends_source` is `none` · `date` · `marathon`. `buffer_days` null = the server default, which is `buffer_default`.
- `wearing` = people wearing ANY of the menu's roles right now; `null` while Discord has not sent the whole member list.
- `ends_held_at` set = a marathon read proposed this EARLIER end and it is waiting: show it and offer *Use the earlier end*.
- `ended_at` set = the end pass has run; `last_pass.members` people lost roles, `last_pass.failures` still wear one.
- `mode`, `channel_id`, `message_id`, `approval`, `expires_days`, `retry_days` are RETIRED — still in the row so the old page loads;
  dispatch 2 stops reading them, and they are ignored on write.

**`GET /api/rolemenus/marathons`** — what a menu can end with, still-to-end first:
`[{"id": "24", "name": "Back to Black 2027", "ends_at": "2027-02-28T05:00:00+00:00", "label": "Back to Black 2027 · ends 2027-02-27"}]`
(`ends_at` null → label *… · end not known yet*). The panel's 25-cap does not apply here; the site may show them all.

**`POST /api/rolemenus`** `{"name": "btb-2027", "title": "Back to Black 2027", "description": ""}` → the row above.

**`PUT /api/rolemenus/{name}`** — send ONLY the fields that changed. Words/options write one `web.role_menu.edit`; an end writes one
`web.role_menu.end_set`. An end is only touched when the body names one of `ends_source`, `ends_marathon_id`, `ends_at`,
`buffer_days`, so a words-only save never re-arms an ended menu — and ANY end write clears `ended_at` (that is how a menu is reused).

| Body | Effect | Refusals (400) |
|---|---|---|
| `{"ends_source": "date", "ends_at": "2027-02-28"}` | ends 23:59 guild-local that day; `"2027-02-28 18:00"` or a full ISO moment also work | `bad_date`, `past_date` |
| `{"ends_source": "marathon", "ends_marathon_id": "24", "buffer_days": 1}` | follows the marathon's end + buffer; omit `buffer_days` to keep the menu's own (or the default), `""`/`null` = default | `no_such_marathon`, `bad_buffer` (0–365) |
| `{"buffer_days": 2}` | changes the buffer of a menu that already follows a marathon | `buffer_needs_marathon` |
| `{"ends_source": "none"}` | no end (ask first on the page — *No end*) | `bad_end_source` |
| `{"options": [...]}` | as before; a role Black Bloc could not take off is refused | `role_refused` (`rolemenu_cannot_strip_said`) |

**`POST /api/rolemenus/{name}/end-now`** `{}` — the end pass now. Ask first with the counts: *Take {options.length} role(s) off
{wearing} people now?* (`rolemenu_end_now_question`). 200 → the row + `"message"` (the ended sentence) + `"pass": {"members",
"this_pass", "failures", "passes", "ended"}`. 409 `test_mode` under the guard; 409 `members_not_loaded` when the member list would
not load (nothing changed).

**`POST /api/rolemenus/{name}/end-earlier`** `{}` — take the held earlier end. 200 → the row; 409 `nothing_held`.

**`DELETE /api/rolemenus/{name}`** — 409 `menu_still_ends` while the end is still ahead and someone wears a role (the sentence says
*End it now* first, or *No end*).

**`POST /api/rolemenus/{name}/assign`** `{"user_id", "role_ids": [...], "remove": false}` — as before, no longer refused by any
mode; grants are written with the menu's end.

**Retired (410 `rolemenu_retired`, sentence `rolemenu_retired_said`)** — the page must not call them: `POST /{name}/post`,
`POST /{name}/unpost`, `GET /requests`, `POST /requests/{id}/approve|deny`, `POST /seed`.

**Members** — `GET /api/members` chips: `roles[].expires_at` is now the sooner of the grant's end and the role's menu end (so a
by-hand wearer with no grant row gets the chip), and `roles[].ends_with_menu` names the menu (null otherwise). The existing chip code
therefore already draws *ends <date>* for menu roles; dispatch 2 only needs to say *with {menu}* if wanted.

**Timed roles** — `POST /api/roles/grants/{id}/extend` answers 409 `menu_end` (`rolemenu_push_back_refused`) for a role on a menu
with an end; `POST /api/roles/grants` clamps `days` to the menu's end.

**Settings** (Role menus tab, namespace `rolemenu`): `rolemenu_end_earlier_holds`, `rolemenu_end_buffer_days`,
`rolemenu_end_moved_minutes`, the two notice switches and every `rolemenu_*` sentence of §3.4/§6.4. `rolemenu_mode` and the four
`rolemenu_off_*` keys are gone from `/api/settings` (the page's mode switch shows its "did not report a key" sentence until dispatch 2).

### 6.4 What 1b built, and every deviation or decision it took (2026-11-13, branch `temp-roles-menu`)

Code notes: [`code-notes.md`](code-notes.md) ▸ *Temporary roles, the staff control*.

1. **The earlier-end hold (conductor's addition, not in §3).** Schema 108 adds `role_menus.ends_held_at`. A marathon read that would
   pull a bound menu's end earlier than its end OR the last end staff were told, by MORE than `rolemenu_end_moved_minutes`, is not
   applied while `rolemenu_end_earlier_holds` (bool, **default on**) is on: the candidate is stored, `role_menu.end_held` logged
   (important), one notice posted (`rolemenu_end_held_text`, again only if a later candidate moves past the floor), and the card shows
   *Held: …* and **Use the earlier end** (API `POST /{name}/end-earlier`). A later read that no longer pulls earlier clears it
   (`role_menu.end_hold_cleared`, routine). Staff-set dates and *End it now* are never held. Off = 1a's behaviour.
   - Decision: comparing against the TOLD end too (not only the current end) so many sub-floor earlier moves cannot creep the end.
   - Decision: the held notice ignores `rolemenu_end_moved_notice` — it is the only way staff learn something waits on them.
2. **Retired keys: five, not three.** `rolemenu_mode`, `rolemenu_off_confirm_said`, `rolemenu_off_confirm_button` as briefed, and
   ALSO `rolemenu_off_dm` and `rolemenu_off_takes_roles_back`: their only reader was `handed_roles`' role-menu branch, which goes
   with the mode, and a switch on the Settings page that does nothing is a dead control. Rows stay in the database (ignored). ⚠️ For
   the conductor: reversible by re-registering them; say so if they should have stayed.
3. **Per-menu `mode` / `approval` / `expires_days` / `retry_days` / `channel_id` / `message_id`**: kept in the DB and in the GET row
   (so the old page loads), ignored on POST/PUT. New menus are stored `mode = staff`. The New menu modal lost its mode box and the
   card its Rules…/Post…/Take it down; the root lost Seed / mode switch / Waiting on staff.
4. **`_register_panels` did not exist** — the re-registration was inline in `cog_load`. It is removed, and a DynamicItem on
   `rolemenu:<id>` (`RetiredMenuPick`) answers a posted panel's select with `rolemenu_picking_retired_said` (no view registered, so
   nothing double-fires). `RequestButton` answers `rolemenu_retired_said`.
5. **The boot panel sweep is gone** (`rolemenu_panels.reconcile` / `panels_on_boot` / `install`): with the mode retired it would
   have taken every posted panel DOWN, and "nothing is deleted from any channel". `repost` posts nothing (pings' streamer menus
   are no longer re-rendered); `unpost` stays for pings' own take-over.
6. **`/rolemenu` is never hidden** (`command_visibility` lost its `rolemenu_mode` row) and its description no longer mentions
   requests. The root command DEFERS before building (wearer counts may chunk).
7. **Words.** Every new sentence, label, title, placeholder and refusal is a key (`ROLEMENU_STAFF_WORDS`, 45 keys incl. the hold
   switch); modal titles/labels are cut at 45 and buttons at 80 where they render (the brackets precedent). The existing panel
   words 1b did not touch (New menu, Grants…, Words…, Hand roles out…, the grant card) stay constants as before — same open item as
   the sticky panel's.
8. **The Grants… audit**: a role on a menu with an UNFINISHED end is listed by wearers (live) with that end and its grant rows are
   dropped from list and picker; a role on a menu with NO end keeps its grant rows (the design was silent; nothing running
   disappears).
9. **The clamp** reads the soonest UNFINISHED menu end per role, never `menu["ends_at"]` of an ended menu. *Give somebody a role…*
   with 0/blank days on a menu role gets the menu's end (`clamped(None, end)`).
10. **Delete refused** while the end is ahead and anyone (or an unknown number, cache short) wears a role.
11. **Health**: each loop row in `/api/status` gains `counts` (only the role-menu expiry loop fills it: *menus due N · ended N ·
    failures N*, the last tick); the Health page shows it beside *Next run*.
12. **Site, minimum only**: `page-rolemenus.js` no longer calls `GET /requests` on load (an empty list feeds the old Requests
    section) and `shell.js` no longer calls it for the nav badge. Everything else on the page is dispatch 2's.
13. **Mock**: `typedEnd` treats a typed date as UTC 23:59 (the real API uses `default_timezone`); good enough for shapes.

**NOT built in 1b (dispatch 2's):** the page's End editor / End it now / removing Requests, Post, Seed and the mode switch, the
marathon drawer line, the Members chip wording.

### 6.5 What dispatch 2 built, and every deviation or decision it took (2026-11-13, branch `temp-roles-menu`)

Code notes: [`code-notes.md`](code-notes.md) ▸ *Temporary roles, the site*. Verified by eye on the local mock in
`chrome-headless-shell` (1280 px and 390 px); ⚠️ nothing here met Discord or the live site.

**Three fixes to 1b first**
1. **Use the earlier end asks first** (panel and page). The confirm names the held end and the live counts
   (`rolemenu_use_held_question`); when the held end has already gone by it says so and that the roles come off at the next
   hourly pass (`rolemenu_use_held_past_question`); `rolemenu_use_held_yes` is its button. Three new keys. `POST
   /{name}/end-earlier` stays one call; the GET row gains `held_label`, `held_past`, `held_question` and `end_now_question`.
2. **`pings.py`'s words** no longer send staff to *Post it*: the streamer and notifications groupings are called role menus and
   members opt in from `/pings` (`CREATED`, `REUSED`, `RENAMED`, `SETUP_MENU_ADDED`, `SETUP_MENU_THERE` + the mock's copies).
   These were constants, not keys, and stay constants.
3. A test: End it now on a menu holding an earlier end clears the hold and runs the pass once.

**Deviations from §3.6 and the brief**
4. **API fields beyond §6.3** (the page needed them): `pass.left` on End it now (worded lines, one helper shared with the ended
   notice), `ends_with_menu` on every grant row, `role_menus` on every marathon row (unfinished bound menus only). Contract
   entries for all three plus `POST /{held_menu}/end-earlier` on a seeded held menu (both halves).
5. **The drawer line sits under the header's facts line**, not on an "Event card" — the drawer has no card by that name; the
   event switch's line lives inside Settings and is not drawn for every source. One read-only line, drawn only when bound.
6. **The End controls are their own card with their own Save**, beside the words editor, so a words save can never carry an end
   field (any end write clears `ended_at`). The card's "how it ends" is a three-way switch (a marathon / a date / No end).
7. **The page stops drawing `role_menu_channel_id`** (the channel menus were posted in): posting is retired, so it is a dead
   control here. ⚠️ The key is still in the registry and on the Settings page — retiring it is a conductor question.
8. **End it now renders on every menu with roles**, the panel's rule — including menus with no end (an ad-hoc end). The confirm
   names the counts.
9. **Members chips**: the API already merged menu ends; the chip's tooltip now says *ends with <menu>* (the chip's own note was
   already the days left).
10. **The mock** reads typed ends and shows moments in `default_timezone` (1b's §6.4 item 13 is fixed), counts wearers on the
    roster, takes roles off it on End it now (a reset restores them), and seeds one menu per state the page draws.

**Open questions (named, not decided)**
- Retire `role_menu_channel_id` from the registry (item 7)?
- The `streamers` / `notifications` menus are pings' own groupings but now sit on the staff control like any menu: **Set the end
  on one would strip every fan or Events role at its end**, `pings._drop_spare_menus` deletes a streamer menu without
  `delete_refusal`, and `pings._fill_menu` rewrites options without `stamp_grants`. Should pings' menus be hidden from, or
  refused an end on, the staff control?

### 6.6 Pings keeps no role menus (2026-11-13, branch `pings-no-menus`; answers §6.5's last open question)

Owner decision 2026-11-13: pings-owned menus never sit on the temporary-roles control or get an end. Code notes:
[`code-notes.md`](code-notes.md) ▸ *Pings keeps no role menus*.

1. **Pings stops creating and maintaining role-menu rows.** `sync_streamer_menus`, `ensure_notifications_menu` and their helpers
   are gone; a fan role made, renamed, removed or pruned and the Events setup touch no `role_menus` row. Nothing that decides who
   is pinged read those rows. No row is deleted (live had none on 2026-11-13); no migration.
2. **The belt — one check, `role_menus.pings_refusal`:** a menu holding a fan role (member or spotlight) or the Events role
   (`golive_ping_role_id` or `events_ping_role_id`) is refused, in `rolemenu_pings_role_said`, every move that arms an end — Set the
   end (marathon, date, buffer), End it now (before the confirm), Use the earlier end — and *Add a role…* refuses such a role. Both
   doors: the `/rolemenu` panel and the API (409 `pings_role` on PUT end fields, PUT options that ADD one, `end-now`,
   `end-earlier`); the mock mirrors it. *No end*, *Remove a role…* and *Delete* stay open, so a legacy row is never stranded.
3. **Not closed — the reverse order (conductor's call).** A role ALREADY on a menu with an end can still be made a fan role
   (`/pings` ▸ Streamers… with an existing role → `ensure_fan_role(existing_role=…)`) or the Events role (`setup_events_role(role=…)`,
   or the two settings keys set by hand) — and by NAME: the template path of `ensure_fan_role` reuses a same-named role, and
   `setup_events_role` takes a role called `pings_events_role_name` if one exists. Nothing refuses that, and the hourly end pass then strips it from everyone at the menu's
   end. Closing it means either `/pings` refusing a role that sits on a menu with an end, or the end pass skipping `/pings` roles.
4. **Not covered — the raid-train role** (`raidtrain_ping_role_id`), which members also opt into from `/pings`. The decision named
   fan roles and the Events role only; adding it is one line in `pings.owned_role_ids`.

### 6.7 The staff guide and the posting channel (2026-11-13, branch `rolemenu-guide`; answers §6.5's first open question)

Owner decisions 2026-11-13 (Q4 a, Q5 a). Code notes: [`code-notes.md`](code-notes.md) ▸ *The temporary-roles guide and `role_menu_channel_id` retired*.

1. **The staff guide `rolemenu-post` teaches the temporary-roles control** (Q4 a): *Give out temporary roles* — New menu, Add a role, Set the end (a marathon or a typed day), Hand roles out; faults for a role Black Bloc cannot take off, a `/pings` role, a held earlier end, Delete refused; facts `rolemenu_end_buffer_days`, `rolemenu_end_earlier_holds`, `rolemenu_approval_channel_id` (it still has a job: role notices). The slug stays. ⚠️ A deploy re-points *Put the original back* only; the live guide reads the old words until staff press it.
2. **`role_menu_channel_id` is retired** (Q5 a), the `rolemenu_mode` way: out of the registry, Settings, `/settings` ▸ Roles & channels, the mock and the contract; a stored row is kept and ignored. Keys 1470 → 1469. Its readers had no job left: the Roles & channels picker (a dead control), the chat's *the menus are posted in* sentence (behind `picking_is_on`, always False), the page (dropped in §6.5 item 7).
