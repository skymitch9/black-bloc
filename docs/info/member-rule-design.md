# The member rule — a timed-role holder without a member role is not BaF

> **Audience:** the conductor, the build agent, reviewers. **Status:** TRACKED. **Last verified: 2026-11-24** — against
> branch `member-rule` (off `main` `1b2a8e8b`) by the hermetic suite and the mock check. ⚠️ **NOT checked:** the live
> server (who holds Member, which roles are on the timed list), the live database, Discord, a browser. Secret NAMES only.
> **State: 🔨 BUILT on branch `member-rule`, NOT merged, NOT deployed.** The key ships blank, so the rule is OFF.

## The ask, verbatim (owner, Tue 2026-11-24 23:1x Phoenix)

*"make sure people with temporary roles as managed by role menu arent counted as black streamers if they dont have
member role"*

## The rule

| Who | BaF? |
|---|---|
| `marathon_member_role_ids` blank | unchanged — exactly today's behaviour; the timed list is not even read |
| wears a role on the timed list (`timed_roles.role_ids`) and **none** of `marathon_member_role_ids` | **not BaF** |
| wears a timed role and at least one member role | unaffected |
| wears no timed role | unaffected, whatever else they wear |
| has a `marathon_baf_overrides` row (*Count as BaF anyway*) | BaF — staff final say wins |

It lives inside the ONE computation, `marathon_announce.not_ours` (predicate `left_by_member_rule`), called only through
`cogs/content/marathon.not_ours_of`, so every consumer inherits it: the rematch (`cog.rematch`), Hotfix
(`marathon_feeds`), `baf_runs`, and the Members page's Opted out list (`api/tools/optouts.marathon_chips`, which used to
compute the opt-out holders itself and now reads `not_ours_of`). A person left out is marked exactly as an opt-out-role
holder is (`not_ours = "role"`, `not_ours_id`), so the site's *Count as BaF anyway* move works unchanged.

## Its words

`marathon_not_baf_member_word`, default `not BaF (no {role} role)`, `{role}` = the FIRST role of
`marathon_member_role_ids` in its stored order. `baf_rule` (`held_said`) picks the reason per person: someone who also
wears an opt-out role reads the opt-out reason (`marathon_not_baf_role_word`). Both keys are editable on Settings and
through `/settings` (not site-only — checklist 33).

## Re-match

| Change | What runs |
|---|---|
| `marathon_member_role_ids` set or cleared (site or `/settings`) | `roles_changed` → `role_rematch` (same hook as the opt-out key) |
| a member's roles change so their standing under the rule flips | `member_roles_changed` → `member_rule_flipped` → `role_rematch`; nothing for someone with an override |
| a role joins or leaves the timed list | `role_menus.add_timed_role` / `drop_timed_role` → `timed_list_changed` → `role_rematch`, only while the key is set |

The opt-out branch of `member_roles_changed` (and its `clear_by_optout` "latest act wins") is unchanged; an override is
never cleared by the member rule.

## The preview — `GET /api/marathons/member-rule`

Behind the router's staff dependency like its neighbours (the operator token reads every `GET` — `../access/operator-read.md`; NOT exercised with the token here), answers while the key is blank: `member_role_ids`, `on`, `timed_role_ids`, and
`holders` — every non-bot member wearing a timed-list role, each with `user_id`, `username`, `member_name`,
`timed_roles` (names), `has_member_role` (against the key), `has_role_named_member` (a role named exactly `Member`,
case-insensitive), `override`, `left_out` (what the rule does with the current key; always false while it is blank).
`has_role_named_member` is sent ALWAYS, not only while the key is blank: the live contract sweep reads the contract's
keys on every row, so a conditional field would fail it the moment the key is set.

## Known edges (not fixed)

- A `/settings` change of the key logs its rematch rows as `web.marathon.role_opted_*` — the settings hook carries no
  `via` (same as the opt-out key, which is site-only so it never mattered).
- People left out by this rule reuse the `marathon.role_opted_out` / `role_opted_in` log kinds.
- The Members page links every `marathon_role` chip to `#marathon_optout_role_ids` (`page-members.js`), also for people
  this rule left out.
- No `on_guild_role_delete` prunes `roles` keys anywhere: a deleted member role left in the key leaves out EVERY
  timed-role holder until staff fix the key.
- An event end that strips timed roles in bulk flips each stripped non-member back in, one full rematch per member.
