# Opted-out roles (GDQ `Staff`) + the global opt-out list

> **Audience:** the conductor, the build agent, reviewers. **Status:** TRACKED. **Last verified: 2026-10-18** — against
> `main` `58fb50ab` by reading the code named below. ⚠️ **NOT checked:** the live server (who holds `Staff`, whether
> that role can see the staff channel), the live database. Secret NAMES only.
> **State: 🔨 BUILT on branch `optout-roles` (off `main` `c009d4fc`), NOT merged, NOT deployed** — see *As built* below.
> ~~State: 📝 DESIGNED, owner sign-off pending — nothing built.~~ (signed off 2026-10-18, the four decisions below)

## The ask, verbatim (owner, Sun 2026-10-18 15:1x Phoenix)

*"we need to work on opting out the Staff role which is currently only used by GDQ Staff. They arent technically Black
in a Flash members so we don't want them being tracked in the marathons as such. I want them to go through our current
paradigm and not a different exclusion function. can we add that role to the opt list? maybe add a global opt out list
so once we opt someone out of something we have an easy way to see every opted out perosn. talk to me about the design
before finalizing"*

## Decisions (asked one at a time, 2026-10-18 15:2x)

| # | Question | Answer |
|---|---|---|
| Q1 | What does a role opt-out mean? | **B — not BaF at all.** The matcher treats the holder like an unmatched name: no ✦BaF, no staff-thread runner posts, never the reason a Hotfix show is tracked, no public post. |
| Q2 | Do hand opt-outs change meaning? | **B — two levels.** A hand opt-out (per person, per marathon, `marathons.announce_opt_out`) stays *posts-only*; the member is still tracked. Words on the site: *opted out of posts* vs *not BaF (Staff role)*. |
| Q3 | The staff override for a `Staff` holder who IS BaF | **A — one per-person switch, global across every marathon.** *"A but these kind of controls need to be website only"* |
| Q4 | What the global list covers | **A — every feature now**, on the Members page. |

## 1. Today's paradigm (read 2026-10-18)

- `marathon_announce.opted_out(marathon)` → the per-marathon id set; `decide()` reads it; one writer
  `cogs/content/marathon_announce.set_opt_out` (under the marathon lock).
- `marathon.match_people()` decides who is ours (pairing → Twitch link → exact Discord username); `ours()` /
  `is_ours()` read its `user_id`. Callers: `cogs/content/marathon.py` `rematch()` and `marathon_hotfix.matched_of()`.
- No setting anywhere acts on a role to exclude someone — the role rule is new, but it lives in the opt-out module.

## 2. The role opt-out

- **Setting `marathon_optout_role_ids`** (registry, kind = role list, default `[]`, label editable). The owner picks
  `Staff` on the site after the deploy — the code never names the role.
- **One function, in the opt-out module** (`marathon_announce.py`, beside `opted_out`): `not_ours(guild, store,
  overrides) -> frozenset[int]` = members holding any listed role, minus the override set. Only module that answers
  "is this person excluded by role".
- **The matcher takes it as an input** (`match_people(..., not_ours=...)`): a matched id in the set is dropped to
  `user_id = None` and the person carries `"not_ours": "role"` so the board can say why. Every caller passes it, so
  the Hotfix tracking reasons follow automatically. Pairings are NOT exempt — a staff pairing of a `Staff` holder is
  still not ours until overridden (one rule, no back door).
- **When it applies:** on every rematch, plus an immediate rematch of every live/upcoming marathon when the setting or
  an override changes, and on `on_member_update` when a member gains or loses a listed role.
- **Public posts already up** that now name nobody are taken down exactly as a hand opt-out does (edited to
  `marathon_public_removed`, never deleted); un-excluding puts them back in place — the existing opt-out/opt-in flow,
  reused.
- Logs `marathon.role_opted_out` / `marathon.role_opted_in` (members, via) through `log_action`.

## 3. The override — *Count as BaF anyway* (website only)

- **Table `marathon_baf_overrides(user_id INTEGER PRIMARY KEY, by INTEGER, at TEXT)`** — schema 94 → 95, migration
  before deploy.
- `POST` / `DELETE /api/marathons/baf-override/{user_id}` (staff-gated, `web.` log kinds). Shown as a control on the
  person's People-card line and on their global-list row; the board says *BaF (staff override)*.
- Hand opt-outs still apply on top of an override.

## 4. Website only — a recorded exception to checklist item 33

Owner, Q3: the role list and the override have **no Discord button, panel or slash path**, and `/settings set-value`
does not offer `marathon_optout_role_ids`. This is the deliberate exception to "every decision is configurable both
ways"; the site is the one place they are changed.

## 5. The global opt-out list — Members page

- A new filter on `members.html`: **Opted out**. One row per person, a chip per place they are out of:

  | Chip | Source (unchanged store) |
  |---|---|
  | Marathons — *not BaF (Staff role)* / *BaF (staff override)* | `marathon_optout_role_ids` + `marathon_baf_overrides` |
  | Marathons — *opted out of posts* · named marathons | `marathons.announce_opt_out` |
  | Go-live | `golive_optout` |
  | Chat memory | `chat_memory_optout` (read with the guild's consent default — a row means *off the default*) |
  | Birthdays | `birthdays.opted_in = 0` |
  | PBs | `pb_matches` `state = 'opted_out'` |

- A filter chip per source; each chip links to where that opt-out is undone. **Read-only roll-up — no new store, no
  copy of any opt-out**, one reader per source (one fact, one home).
- Marathon channel opt-outs (`optout:{login}` keys) are Twitch channels, not people: a small *Channels* section on the
  same view.
- `GET /api/members/optouts` returns the rows; no blurb on the page (owner rule 2026-10-04).

## 6. Dry run (owner: *"dry run everyone with the staff run and tell me who they are"*, read 2026-10-18 15:3x Phoenix)

Read through the operator token (`/api/ref/roles`, every page of `/api/members` — 123 of 123, `/api/marathons` and each
`/{id}/people`). Nothing changed.

- Role **`Staff`** = id `1335035657730523219`, position 53 of 58, not managed.
- **Six holders**, none of them bot staff (`staff: false` on the Members read): Ashley (`ashleyawoww`), UraniumAnchor
  (`uraniumanchor`), ogNdrahciR (`ogndrahcir`), GDQ Tech - Richard (`gdqtech`), Raelcun (`raelcun`), so (`_so_`).
- **Matched as BaF today: one** — Raelcun, *host*, matched by Discord name, the ONLY BaF person on marathon 18
  *Special Event* (runs 287-289) and marathon 19 *GDQueer (Oct 2026)* (runs 290-292), all 2026-10-20 23:00Z to
  10-21 01:59Z. Both are `gdq_hotfix`, untracked (`tracked_state` found), `opted_out: false`. With the role opted out,
  both boards would show nobody from BaF.
- ⚠️ NOT read: archived marathons; pairings of the six by id; Members shows a member's top 5 roles only, so a holder
  with 5+ roles above position 53 would be missed (all six list `Staff` first).

## 7. Not decided here / to verify on build

- Whether the GDQ `Staff` role can see the staff channel (if so it would also be bot staff via
  `resolved_staff_roles`) — a live read, reported, not changed.
- How many current holders and how many runs/highlights change on the first rematch — measured after deploy, both
  numbers reported.

## As built (branch `optout-roles`, 2026-10-18)

| Part | Where |
|---|---|
| Setting `marathon_optout_role_ids` (roles, default `[]`) | `settings_store.MARATHON_SETTINGS`; `SITE_ONLY_KEYS` |
| Website only | `settings_panel.keys_in` leaves it out of `/settings`; `cogs/core.leads_only` refuses it off the site (403 `site_only`, in words). The recorded exception to checklist 33 (`tests/test_settings_store.py::test_every_registry_key_is_reachable_from_the_panel_as_well_as_the_dashboard`) |
| The rule | `marathon_announce.not_ours(guild, store, overrides)`; `match_people(..., not_ours=)` → `user_id None`, `not_ours: "role"`, `not_ours_id` |
| Callers | `Marathons.rematch`, `marathon_hotfix.matched_of` (Hotfix tracking + picker) |
| Override | table `marathon_baf_overrides(user_id PK, by, at)`, **schema 94 → 95**; writer `cogs/content/marathon_announce.set_baf_override`; `POST`/`DELETE /api/marathons/baf-override/{user_id}` → `{user_id, override, message}` |
| Rematch at once | `role_rematch` on the setting (`store.on_change`, registered in `Marathons.cog_load`), on an override, on `on_member_update` (members intent is on) |
| Posts | the hand opt-out's own `followed` path: a highlight naming nobody is edited to `marathon_public_removed`, put back in place on re-inclusion |
| Logs | `marathon.role_opted_out` / `role_opted_in` (`members`, `marathons`, `via`), `marathon.baf_override_set` / `_cleared` (+ `web.` twins), all IMPORTANT |
| People board | `baf_rule` on every row: `{state: role\|override, user_id, member_name, said, move: set\|clear, move_label}`; the site draws the words + one button on the slot line (role) and the BaF row (override) |
| Global list | Members ▸ **Opted out**; `GET /api/members/optouts` → `{people[{user_id,name,username,avatar,here,chips[{source,said,marathons,rule}]}], channels[{id,login,name}], sources}`; `api/tools/optouts.roll_up`, read-only |
| Keys | **+8** (1220 → 1228): `marathon_optout_role_ids`, `marathon_not_baf_role_word`, `marathon_baf_override_word`, `marathon_posts_opted_out_word`, `marathon_baf_override_button`, `marathon_baf_override_clear_button`, `marathon_baf_override_set_said`, `marathon_baf_override_cleared_said` (registry + mock row + label) |
| Routes | **+3** (`check.mjs`: 27 pages, 368 routes) |

### Deviations

1. **Channel opt-outs read `spotlight_channels.marathons = 0`, not the `optout:{login}` keys.** Those keys are the boot seed's done-once markers (`marathon_channels.seed_key`); the opt-out itself is the column. Shown under *Channels out of marathons*, linking to Go-live.
2. **Chat memory under `optin` consent lists nobody**: everyone is off by default there, and a row means *opted in*.
3. **Logs are per trigger, not per member**: one `role_opted_out` row naming every member whose held state changed on some live/upcoming marathon. A role holder on no marathon changes nothing, so logs nothing.
4. **A role-held person on a slot shows the rule instead of *Link to a member…*** — a pairing cannot make them ours, so the button would mislead.
5. Members-page source chips and their labels (*Marathons*, *Go-live*, …) are site chrome in `page-members.js`; the marathon words on each chip come from the keys.

### Measured (on the branch)

- `pytest -q -n 16`: 13372 passed, 1 skipped; `ruff check .` clean; every `site/public/assets/*.js` parses; the 13 node fixture suites the gate runs pass; `node site/mock/check.mjs` against the mock on port 8871: *27 pages, 368 routes, 349 core settings*.
- In a browser against the local mock: Members ▸ Opted out draws Dax (*BaF (staff override)* + Undo), QuietKid (*not BaF (Staff)* + Count as BaF anyway, Go-live, Personal bests), spamlord99 (Chat memory), ESA under Channels; Count as BaF anyway flipped QuietKid's chip and said so; the People card's Super Mario 64 slot shows *not BaF (Staff)* + Count as BaF anyway on QuietKid.

### NOT verified

- Nothing ran against Discord or the live database: not the real `on_member_update` event, not the six `Staff` holders, not how many runs/highlights change on the first rematch (§7 — measure after deploy, both numbers).
- Whether the GDQ `Staff` role can see the staff channel (§7) — not read.
- An excluded HOST's block post: the block vanishes, so it is left to `sync_host_highlights`' left-behind walk on the next tick; no test covers it.
- The schema 95 migration on a copy of the live file.
