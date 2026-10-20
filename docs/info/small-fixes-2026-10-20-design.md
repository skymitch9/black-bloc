# Small fixes, 2026-10-20 — Upcoming follows its mode, birthday privacy, off takes roles back, the `__main__` guard, the stale row

> **Audience:** the conductor (merge + deploy), reviewers, and later sessions. **Status:** TRACKED ·
> 🔨 **BUILT on branch `small-fixes`** (off `main` `d19dcf51`, v245), **NOT merged, NOT deployed**.
> **Last verified: 2026-10-20 04:0x Phoenix.** Measured on the branch: `pytest -n auto` and `ruff check .`
> (figures in the merge report), `node site/mock/check.mjs` ok against a FRESH mock (port 8862, nonce
> `sfix-2`: 28 pages, 375 routes, 353 core settings, all keys present), every `site/mock/*.test.mjs` ok,
> registry `len(KEY_TYPES)` **1241** (was 1233, read live through `scripts/read.ps1 -Path /api/settings`
> 2026-10-20 03:5x), Go-live page keys 89 → **92**. Live grant counts read through `scripts/read.ps1`
> the same hour (§3). ⚠️ **NOT verified:** anything in Discord (the `/pings` and `/rolemenu` confirm cards
> and `/settings` were exercised only with test fakes); the take-back against live members (live has
> nobody to take from, §3); the boot migration against the live database (fixture only); phone width.

Owner decisions 2026-10-19, sheet items **i3**, **i6**, **i7b** of
[`switch-audit-2026-10-19.md`](switch-audit-2026-10-19.md) §5 (**i7a was a No**: never hide a command that
holds a member's own opt-out). Plus two leftovers: the `__main__` guard
([`gotchas.md`](gotchas.md), first entry) and the stale `rehearsal_note` row. Build 6 of the sheet; builds
1–5 are LIVE (v241–v245).

## 1. i3 — a live block shows only while its feature is on

| Block | Before | After |
|---|---|---|
| Upcoming events (`events.py` `upcoming_block_*`) | events loaded only when `on`, block blanked only when `off`: in test, an empty *Nothing is on* card | drawn only when `events_mode` is `on` |
| Who's live now (`golive.py` `block_is_on`) | drawn while `golive_mode` was not `off`, but only `on`-mode sessions were listed: in test, an empty *Live now* card | drawn only when `golive_mode` is `on` |
| Temp voice lobby (`tempvoice.py` `shows_block`) | already `on` only | unchanged, now through the shared rule |

One rule: `block_look.shows(mode)` (`== "on"`). The preview (`preview.py`) and the mock's `PREVIEW_BLOCKS`
follow it. Tests: three states each (`tests/test_block_look.py`, `test_events.py`, `test_golive.py`).
Live today `events_mode` and `golive_mode` are both **on**, so nothing a member sees changes.

## 2. i6 — birthday opt-out hides the date from other members

| Who looks | Before | After |
|---|---|---|
| A member, someone who opted out | the date | `birthday_not_shared_said`: ***Nadia** keeps their birthday to themselves.* |
| Staff, someone who opted out | the date + *They are opted out* | unchanged |
| Anyone, their own | the date (+ *You are opted out*) | unchanged |

The opt-out is now read from the `birthday` kind of `optouts.py` (v245) on the card, the panel's own
opted-out state, *Next birthdays* and the staff month list. Before, all four read the old
`birthdays.opted_in` column. Both stores are still written by `set_opted_in`, so they agree.

**The month list (`MonthSelect`), traced:** it is **staff-only** twice over. It is added to the panel only
for staff, and `send_month` re-checks `still_staff`. It never leaked to members. It marked *opted out* from
the old column, and now marks it from the kind. *Next birthdays* (members see it while
`birthday_panel_show_next` is on) already left opted-out people out, and now reads the kind too.

The wording has a preview: Settings / Birthdays page ▸ *What a member sees looking up someone who opted
out* draws the lookup card (`preview.py` renderer `birthday_lookup`, mirrored in the mock).

## 3. i7b — turning a feature off takes back the roles it handed out

### Inventory

| Feature | Hands out member roles through | Records what it handed out | In this build |
|---|---|---|---|
| Pings (`pings_mode`) | `/pings` follow a streamer, the Events / raid-train toggle | its own action-log rows: `pings.follow` / `pings.unfollow`, `pings.events_on` / `pings.events_off` (with `role_id`, target = member). The log is never pruned. | **yes** |
| Role menus (`rolemenu_mode`) | posted menus (self-pick), approval requests, the staff picker | `role_grants`, source `menu` / `approval` / `staff` / `manual` | **yes**: `menu` and `approval` only |
| Applications (`applications_mode`) | an approved application | `role_grants` source `approval`, linked by `applications.grant_id` | **no** (deviation 1) |
| Marathon role block | a toggle button on a post | nothing | no: no mode hides it, so the member's own way out stays |
| Go-live live role, birthday role | automatic, for the stream / the day | the session / the birthday row | no: not handed out through a panel, and taken off on their own |

### Live grant counts (2026-10-20 03:5x, `scripts/read.ps1`)

| Feature | Live mode | Ledger rows | Would be taken back today |
|---|---|---|---|
| Pings | **on** | `pings.follow` 0, `pings.events_on` 0, `web.pings.follow` 0 (`/api/actions?kind=…`) | **0** |
| Role menus | **off** already | `/api/roles/grants` 0 rows; both menus unposted | **0** |

Live members wear the Events and Raid-train roles through Discord onboarding (`/api/pings/onboarding`
managed), not through pings, so none of them is touched. `/api/pings/streamers` is empty, so there are no
fan roles.

### What happens

`black_bloc/handed_roles.py` owns the dry run (`held`), the question (`asked`) and the take-back
(`take_back`). It never touches a role it cannot prove it put on:

- **Pings:** a member and role whose newest ledger row is a give, and who still wears the role.
- **Role menus:** an open `role_grants` row of source `menu` or `approval`, for a role that is an option on
  one of this guild's menus, not linked from an application, and still worn. A role staff handed over, one
  added by hand, or an application's role stays.

The confirm flow, everywhere `off` can be written:

| Where | Flow |
|---|---|
| Site (Settings page, Go-live strip, Role menus switch) | `PUT /api/settings/{key}` answers `409 confirm_needed` with the count sentence; the page's *Are you sure?* dialog; *Change it* resends with `confirm: true`. Reset (`DELETE`) the same, since both defaults are `off` |
| `/settings` key card (buttons, typed value, reset) | the same 409 from `set_key` / `clear_key`; the card shows the sentence with `pings_off_confirm_button` / `rolemenu_off_confirm_button` and **Leave it as it is** |
| `/pings` ▸ Settings mode select | confirm card: **Yes, switch pings off** / **Keep it** |
| `/rolemenu` mode button | confirm card: **Yes, switch role menus off** / **Leave it** |

Nothing is asked when nobody would lose a role. The take-back runs from a store hook installed in
`setup_hook` (`install_handed_roles`), so every write that leaves the key `off` takes back, whatever path
made it. One log row per feature, `pings.roles_taken_back` / `role_menu.roles_taken_back` (important, posted
to the log channel): `{key, members, roles, failed, dms, taken: [[user, role], …]}`. A role Discord refuses
to remove is counted `failed` and stays on the ledger. Pings also writes its own `pings.forbidden`. A DM
goes only to role-menu members whose role was **approved** (`rolemenu_off_dm`), the one path that DM'd on
the grant. Pings never DM'd on a grant, so it sends none. Under `TEST_MODE` the take-back is only logged
(`*.would_take_back`, checklist 1).

**Switching back on gives nothing back.** The key help says so. A role a member gets again later from
elsewhere is no longer the feature's to take, because the take-back row closes the ledger.

**Staff final say:** `pings_off_takes_roles_back` / `rolemenu_off_takes_roles_back` (bool, default true)
turn the take-back off, so staff can switch a feature off and keep every role.

### Keys (registry 1233 → 1241)

`birthday_not_shared_said`, `pings_off_confirm_said`, `pings_off_confirm_button`,
`rolemenu_off_confirm_said`, `rolemenu_off_confirm_button`, `rolemenu_off_dm` (text);
`pings_off_takes_roles_back`, `rolemenu_off_takes_roles_back` (bool). Help rewritten: `pings_mode`,
`rolemenu_mode`, `birthday_panel_lookup`.

## 4. The `__main__` guard

`black_bloc/__main__.py` runs `main()` only under `if __name__ == "__main__":`. `python -m black_bloc` is
unchanged (`tests/test___main__.py` runs the package through `runpy` under a fake `main`, and imports it
under the same fake, asserting it was not called). `app.py` only defines `main`. Its imports load `bot.py`,
`config.py`, `errors.py` and `logging_setup.py`, which have no top-level calls. Gotcha marked *FIXED by
v246*.

## 5. The stale `rehearsal_note` row

`rehearsal_note` joined `shadow_one_meaning.RETIRED_KEYS`, the drop list of the existing idempotent boot
migration. No new mechanism. The boot's *settings ignored: rehearsal_note* line stops after the first v246
boot, and that boot writes one `settings.migrated` row naming it. Dry run against the v243-era live mirror
plus the blank row (`tests/test_shadow_one_meaning.py`, run twice, identical):

```json
[{"guild_id": 1073710702776299640,
  "drop": {"youtube_live_mode": "on", "spotlight_mode": "on", "modmail_enabled": true,
           "youtube_mode": "on", "rehearsal_note": ""},
  "write": {"golive_youtube": {"before": null, "after": true}}, "notes": []}]
```

v244 already dropped the other four live, so the live run should drop `rehearsal_note` alone. The stored
value is assumed blank from the boot line. Not read.

## 6. Rollback

Redeploy **v245** (`66a8cc34`) and restore the pre-deploy snapshot ([`../access/deploy.md`](../access/deploy.md)).
There is no schema change. The eight new keys are unknown to v245, which logs them as ignored and does no
harm. The dropped `rehearsal_note` row was ignored by v245 anyway. Roles already taken back are **not**
restored by a rollback. They are listed on the `*.roles_taken_back` row (`taken`), and staff can hand them
back from `/rolemenu` or `/pings`.

## 7. Deviations

1. **Applications are not in the take-back.** An application role is a staff decision (approve with a
   reason). No member self-service button is lost when `/apply` hides, so i7's "no way out" does not apply,
   and switching applications off to pause new ones would strip every approved member. Staff-handed menu
   roles (source `staff`, including timed roles) are left out for the same reason, and the `rolemenu_mode`
   help already promised timed roles stay. **Owner call if he wants them in.**
2. **Live now changed too.** The audit said live-now already hid outside `on`. It did not: it drew in test
   with no streams (same empty card). It now follows the same rule.
3. **Two bool switches were added** (`*_off_takes_roles_back`, not in the brief) for checklist 33 and staff
   final say: without them there was no way to switch a feature off and keep roles.
4. **No ask when nobody would lose a role.** The confirm is for the bulk action, and a zero is not one.
5. **The site dialog keeps its generic *Change it* / *Cancel*** (from v245). The bot-side buttons carry the
   per-feature words.
6. **The confirm card buttons** reuse the existing *Keep it* (`/pings`) and *Leave it* (`/rolemenu`) words of
   those panels. *Leave it as it is* stays on `/settings`. They are not keys, the same as every other confirm
   card's way back.

## 8. What was verified on the local mock (fresh, port 8862, nonce `sfix-2`, Chrome)

- Settings page, `pings_mode` filtered: On, saved; Off, *Save changes*. The *Are you sure?* dialog said
  ***2** members hold ping roles Black Bloc handed out; switching pings off removes them.* *Change it*
  saved `off`, and `/api/actions?kind=pings.roles_taken_back` held one row: `members 2, roles 3, failed 0,
  dms 0`.
- Settings page, `birthday_not_shared_said`: the Discord preview drew ***Nadia — birthday** / **Nadia** keeps
  their birthday to themselves.*
- `curl` on a first fresh mock (8861, `sfix-1`): `rolemenu_mode` off asked ***1** members hold roles the role
  menus handed out…*.
- The migration dry run: §5.
