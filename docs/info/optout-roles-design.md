# Opted-out roles (GDQ `Staff`) + the global opt-out list

> **Audience:** the conductor, the build agent, reviewers. **Status:** TRACKED. **Last verified: 2026-10-18** — against
> `main` `58fb50ab` by reading the code named below. ⚠️ **NOT checked:** the live server (who holds `Staff`, whether
> that role can see the staff channel), the live database. Secret NAMES only.
> **State: 📝 DESIGNED, owner sign-off pending — nothing built.**

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
