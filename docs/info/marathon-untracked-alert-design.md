# Untracked alert — a marathon with BaF on it that nobody tracked, flagged to a role before it starts

> 🔨 **2026-10-14 — BUILT on branch `untracked-alert` (off `main` `1a843655`), NOT merged, NOT deployed.** Schema stays **94** (one nullable column through `ADDED_COLUMNS`, the `stale_clock_at` precedent), keys **1213 → 1216**, one new IMPORTANT log kind. Deviations and *What was NOT verified* at the foot.

> **Audience:** the conductor (merge + deploy + setting the live role), reviewers, and the next session touching the marathon tick, the inbox or Track. **Status:** TRACKED.
> **Last verified: 2026-10-14** — by the build's own gate on the branch (ruff, the hermetic suite, the site node tests, `check.mjs` against a mock started from the worktree on `MOCK_PORT=8831`, and each rule switched off in turn to see a test fail). ⚠️ Nothing met live Discord, the live database or Fly; nothing was drawn in a browser. Secret NAMES only (none here).

## The ask, verbatim

Owner, 2026-10-14: *"We need a feature to alert the Aunties and Uncles role when a marathon that has a BaF member or host has not been tracked and the event is 36 hours away from beginning. That way we don't snub the 24 hour check."* Option (a) chosen: a reply in the marathon inbox.

Why: an untracked marathon (found, Track never pressed) posts nothing (`marathon-inbox-design.md` B2), so its public 24-hour reminder never goes out.

## The rule

On the minute tick, under the marathon's lock, after the inbox message is synced and only for an **active** marathon (`Marathons.tick_marathon` → `cogs/content/marathon_untracked_alert.alert_if_due`), the alert is wanted when ALL hold (`marathon_untracked_alert.wanted`):

| Condition | Read from |
|---|---|
| `marathon_untracked_alert_hours` > 0 (default **36**, 0–336; 0 = never) | the key |
| the marathon is live (not archived), active (not paused), **found** — not tracked, not ignored | `marathon_inbox.state_of`, `active` |
| not alerted before | `marathons.untracked_alert_at` is NULL |
| a known start: `starts_at`, else the earliest `scheduled_at` among its non-dropped runs | `marathon_untracked_alert.start_of` |
| `now < start <= now + hours` — found later than 36 h out → the first tick; already started → never | |
| at least one BaF member on a non-dropped run | `marathon_untracked_alert.baf_of` |

**Who counts as BaF** is the matching the bot already did (`marathon.match_people`, which honours `marathon_match_hosts` and the per-marathon host scan): a person on a run with a `user_id`. Hosts (`part = host`) count whether or not `marathon_hosts_count_as_ours` is on — the ask names hosts explicitly. Runners and commentators count unless their match was marked `counts: false`. One member on many runs counts once.

## Once per marathon

`marathons.untracked_alert_at` (TEXT, nullable; `ADDED_COLUMNS` + the CREATE; the archive twin gains it by the mirror) is stamped **before** the send (the `late_track` precedent: cleared/stamped before posting), so a failed send is logged and never retried in a loop. Pressing Track afterward needs nothing: a tracked marathon is never wanted, and the stamp stays.

**The one exception: no role.** With `marathon_untracked_alert_role_id` blank, or set to a role the server no longer has, nothing is stamped, nothing is sent, and one `skipped` row is logged per marathon per reason per boot. The alert goes out on the first tick after a role is set, if the marathon is still in its window. This keeps a deploy with the key still blank from silently using up every marathon in the window.

## Where and how it posts

- **The marathon inbox thread** (`ensure_inbox` — made if missing, re-opened when Discord archived it, the stored id re-read under the inbox lock), as a **reply** to the marathon's inbox message (the one with Track / Ignore). `fail_if_not_exists=False`, so a deleted inbox message still lets the alert post.
- **No inbox message** (or one in the other home, or one mid-move) → posted in the thread without a reply.
- **Mentions:** `AllowedMentions(everyone=False, users=False, roles=[that role])`.
- **Shadow** (`marathon_mode = shadow`): the rehearsal inbox in the shadow home, the shadow note line on top, and **no ping** (`AllowedMentions.none()`) — a rehearsal never wakes real staff (the `pb_feed_ping_role_id` precedent). `off`: nothing (the tick does not run `tick_marathon`).
- **Test mode:** the guard's channel check applies; a refused channel is a `failed` row.

## Words

Key `marathon_untracked_alert_template`, default `{role} **{name}** starts {when} ({relative}) and is not tracked. {who}.` (changed 2026-10-14 at the owner's *"Yes"* to naming who is on it; it was `{baf} BaF on it.`). `{who}` is each BaF person once per part, in run order, as `marathon_untracked_alert_runner` (`{who} running`) or `marathon_untracked_alert_host` (`{who} hosting`) words them with `{who}` = `<@id>`, joined by `, `; the send allows the role mention only, so the names render without pinging anyone (`marathon_untracked_alert.py` `parts_of` / `who_of`). Other fields: `{role}` (the mention), `{name}`, `{when}` (`<t:…:f>`), `{relative}` (`<t:…:R>`), `{hours}` (hours left, one decimal), `{baf}` (distinct members, runners and hosts together), `{runners}`, `{hosts}`. A template that will not fill falls back to the shipped words (checklist 17, `marathon.render`).

## Log

**`marathon.untracked_alert`** (IMPORTANT). Details: `marathon_id`, `name`, `starts_at`, `hours_left`, `baf_runners`, `baf_hosts`, `outcome` (`posted` / `skipped` / `failed`), and as they apply `reason`, `role_id`, `shadow`, `shadow_home`, `thread_id`, `message_id`, `reply`. An untracked marathon has no log thread (`log_threads.thread_for` routes tracked ones only), so the row lands in the log channel.

## Staff final say

`marathon_untracked_alert_hours` (0 turns it off) and `marathon_untracked_alert_role_id` (blank sends nothing) on the Settings page and through `/settings set-value`. Track or Ignore in the inbox ends it for that marathon.

## Keys, columns, kinds

| Kind | Name | Notes |
|---|---|---|
| key | `marathon_untracked_alert_hours` | int, 36, 0–336 |
| key | `marathon_untracked_alert_role_id` | role, blank. ⚠️ The conductor sets the live value: `Aunties / Uncles` `1073711363337236601` |
| key | `marathon_untracked_alert_template` | text, fields above |
| column | `marathons.untracked_alert_at` | TEXT, nullable |
| API field | `untracked_alert_at` | on every live and archived marathon row and drawer (`api/tools/marathons.tracking_of`); not drawn on the site |
| log kind | `marathon.untracked_alert` | IMPORTANT |

Each key has its registry entry, help, mock row and label; the hours key its contract min/max.

## Deviations from the brief

1. **No `SCHEMA_VERSION` bump.** The brief said "bump schema"; the repo's precedent for one nullable column is `ADDED_COLUMNS` with no step (`stale_clock_at`, `log_thread_id`), and `ADDED_COLUMNS` runs at every boot. Schema stays 94.
2. **A missing role is not stamped** (above) — it waits and logs once per boot, instead of being stamped and skipped for good.
3. **Paused marathons are never flagged.** The brief said "live (not archived)"; a paused marathon is not read or followed, and staff paused it by hand. Resume makes it eligible again.
4. **Shadow posts without the ping.**
5. **One log kind with an `outcome`**, not a kind per outcome.
6. **The API field is added but not drawn.** Drawing it would need a word key and page code; the brief allowed skipping the drawer.

## Tests, and how each was seen failing

New: `tests/test_marathon_untracked_alert.py` (5), `tests/cogs/content/test_marathon_untracked_alert.py` (14), one each in `tests/storage/test_db.py`, `tests/test_settings_store.py`, `tests/api/tools/test_marathons.py`; the key count test moved 1213 → 1216.

Written after the code. Each rule was then switched off in the source and the two new test files re-run (measured 2026-10-14, the source restored from the commit after each): the tick call removed → 10 fail; the stamp never read → 3; never written → 2; tracked/ignored not exempt → 2; paused not exempt → 1; the window ignored → 2; a started marathon not exempt → 2; no BaF not exempt → 2; hosts not counted → 4; dropped runs counted → 2; the hours key ignored → 2; a missing role stamped anyway → 1; the skip logged every tick → 1; no reply → 1; shadow pinging → 1; the template key not read → 11. The `ADDED_COLUMNS` row removed → the migration test fails. None was run against `main` itself.

## What was NOT verified

- Anything live: Discord (the reply rendering under the inbox message, the role ping actually notifying, a thread re-open), Fly, the live database, the live role id.
- Whether Discord accepts `fail_if_not_exists=False` on a reply into a thread whose referenced message was deleted — the fake channel takes any `reference`.
- The Settings page in a browser: the three keys were checked by `check.mjs` (*all keys present*) and the label test, never drawn.
- That the 24-hour public reminder then goes out once staff press Track — that path is unchanged and not re-tested here.
