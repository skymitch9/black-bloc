# One test channel — `shadow_channel_id` is the only rehearsal home

> **Audience:** the conductor (merge + deploy), reviewers, and later sessions. **Status:** TRACKED ·
> 🔨 **BUILT on branch `one-test-channel`** (off `main` `ac68977c`, v242), **NOT merged, NOT deployed**.
> **Last verified: 2026-10-20 01:1x Phoenix** — measured on the branch: `pytest -n auto` 13,502 passed +
> 1 skipped, `ruff check .` clean, `node site/mock/check.mjs` ok against a FRESH mock (port 8811, nonce
> `otc-1`: 28 pages, 375 routes, 357 core settings), registry `len(KEY_TYPES)` **1230**, the mock's
> `/api/settings` 1230 keys; live values read through `scripts/read.ps1 -Path /api/settings` (operator
> token, 2026-10-20 ~01:0x). ⚠️ **NOT verified:** anything in Discord; the migration against the live
> database (it ran against a fixture mirroring the live API read); whether the live blank overrides are
> stored as `null` rows or simply unstored (the API shows both as blank — the migration drops either);
> phone width.

Owner decisions 2026-10-19, sheet items **p2** and **p4k** of
[`switch-audit-2026-10-19.md`](switch-audit-2026-10-19.md) (§4 P2, §4 *Shadow-only leftovers*): one test
channel instead of a rehearsal home per feature. Builds 1 and 2 of that sheet are LIVE (v241, v242 —
[`posts-one-switch-design.md`](posts-one-switch-design.md) already retired the sticky / question /
frontdoor / poll overrides). This supersedes [`shadow-home-per-feature-design.md`](shadow-home-per-feature-design.md).

## 1. The inventory (live values 2026-10-20 ~01:0x)

| Key | Live value | Reader before this build | Now |
|---|---|---|---|
| `shadow_channel_id` | `1542316174472380517` (same as `log_channel_id`) | `shadow.py` for every feature | **KEPT** — relabelled **Test channel** (labels.js, help, Settings page, Posts page fold) |
| `posts_shadow_channel_id` | `1550284332365783091` (#post-test) | `posts.py` / `sticky_rehearse` / `questions_rehearse` via `shadow.channel_id(feature="posts")` | **RETIRED** |
| `points_shadow_channel_id` | `1550284332365783091` (#post-test) | none since v242 | **RETIRED** |
| `golive_shadow_channel_id` | blank | `cogs/content/spotlight.py` | **RETIRED** |
| `marathon_shadow_channel_id` | blank | `cogs/content/marathon.py` (board, reminders, shoutouts, inbox, feeds) | **RETIRED** |
| `marathon_public_shadow_channel_id` | blank | `marathon_public.py`, `cogs/content/marathon_public.py`, `marathon_host_highlights.py` | **RETIRED** (p4k) |
| `birthday_shadow_channel_id` | blank | `cogs/community/birthdays.py` | **RETIRED** |
| `pb_feed_shadow_channel_id` | blank | `pb_looks.py` | **RETIRED** |
| `brackets_shadow_channel_id` | blank | `brackets_thread.py` | **RETIRED** |
| `structure_backup_shadow_channel_id` | blank | `cogs/moderation/structure_backup.py` (directly, not via `shadow.py`) | ⚠️ **KEPT** — the structure-changed notice names private channels, so it deliberately never falls back to the test channel or the log (audit §4 P2) |

No `applications_` or `events_` override existed. Registry **1238 → 1230** (eight retired); contract
`core_keys` **360 → 357** (pb_feed, brackets and points were core); the Go-live page draws 89 keys (90);
the birthday `/settings` group 27 keys (28).

`shadow.py`'s `home_id`, `channel_id`, `channel_ids` and `find_copy` lost the `feature=` argument —
one code path; `feature_key` / `FEATURE_KEY` / `_override` are gone, and every caller and the mock's
`postsHome` / birthday / pb-feed twins follow. `rehearsal_copy.py` needed no change (it takes a target).
`guard.py` is untouched: it still learns `shadow_channel_id` through `shadow.install`.

## 2. The migration (`black_bloc/one_test_channel.py`)

Runs once per boot in `BlackBlocBot.setup_hook`, after `_migrate_posts_switch` and **before
`install_rehearsal_home`** (so the guard, when `TEST_MODE` is on, learns the copied value). A failure
is logged (`one test channel: the boot migration failed…`) and never stops the boot. Raw SQL; no schema
change. Per guild that has any stored row of the eight keys:

1. Collect the distinct SET values across the stored overrides.
2. **Two or more** → copy nothing, keep `shadow_channel_id`, delete nothing, write one
   `settings.migration_skipped` row `{build, reason: "the set overrides disagree", test_channel,
   overrides}`. ⚠️ It writes that row again at every boot until a Lead resolves it — loud on purpose;
   the conductor decides what to do.
3. **Exactly one** and `shadow_channel_id` is not already it → write it into `shadow_channel_id`.
4. Delete every stored row of the eight keys (blank ones too).
5. One `settings.migrated` row `{build, removed, values, copied}`; the store re-reads. A second boot
   finds nothing and writes nothing (tested twice).

`dry_run(db)` writes nothing. **Dry run against the live-mirroring fixture**
(`tests/test_one_test_channel.py::live_mirror`):

```json
[
  {
    "guild_id": 1073710702776299640,
    "copy": {"key": "shadow_channel_id", "before": 1542316174472380517, "after": 1550284332365783091},
    "drop": {
      "points_shadow_channel_id": 1550284332365783091,
      "posts_shadow_channel_id": 1550284332365783091
    },
    "skipped": null
  }
]
```

The two set overrides agree (#post-test), so the test channel moves from the log channel to #post-test
and two rows go. If the six blank overrides are stored as `null` rows they are dropped too and listed
in `removed`.

## 3. What rehearses where, before and after (live modes 2026-10-20 ~01:0x)

Every feature whose override was blank rehearsed in `shadow_channel_id` = **the log channel**; after the
migration that is **#post-test**.

| Feature | Live mode | Before | After |
|---|---|---|---|
| ⚠️ **brackets** (`brackets_mode`) | **shadow** | new tournament threads made in the log channel | **new tournament threads start in #post-test** |
| Post to test: posts, stickies, weekly question | posts_mode on | #post-test | #post-test (unchanged) |
| Post to test: polls | poll_mode on | the log channel | **#post-test** |
| spotlight (`spotlight_mode`), golive | on | (would rehearse in the log) | nothing changes until someone picks shadow |
| marathon, marathon public highlights / reminders | on | (log) | nothing changes until shadow |
| birthdays | on | (log) | nothing changes until shadow |
| pb_feed | off | — | nothing |
| points | shadow | placement follows `posts_mode` since v242 | unchanged |
| honeypot, automod, raidtrain | shadow | write log rows, never a copy (not `shadow.py` readers) | unchanged |
| structure backup | shadow | its own key, blank → no notice | unchanged |
| ticket button rehearsal, minutes | only under `TEST_MODE` / minutes off | `shadow_channel_id` | #post-test if ever triggered |
| a copy already up in the log channel | — | — | still found and taken down: `channel_ids` hunts the test channel, the guard, the settings test channel, then the log channel |

Members see nothing at once. Staff see one **Test channel** on the Settings page and in the Posts page's
*Settings and logs ▸ Settings* fold, and no per-feature rehearsal key anywhere (Settings, Posts,
Personal bests, Go-live pages; `/settings` groups).

## 4. Rollback

Redeploy **v242** (`9f24ec22`) and restore the pre-deploy snapshot ([`../access/deploy.md`](../access/deploy.md)).
Without the snapshot, after a v242 redeploy set `posts_shadow_channel_id` and `points_shadow_channel_id`
to #post-test (`1550284332365783091`) and `shadow_channel_id` back to the log channel
(`1542316174472380517`) — otherwise v242 sends brackets threads and poll test copies to #post-test, which
is harmless but not v242's behaviour.

## 5. Deviations

1. The Posts page's fold now draws the core `shadow_channel_id` (*Test channel*) beside `posts_mode`
   instead of no home at all — "the Posts page then shows the one global test channel". It is the same
   key the Settings page draws; core keys may be lead-only (`settings_core_keys_admin_only`); how the fold
   answers a non-lead's save was NOT exercised.
2. A disagreement logs `settings.migration_skipped` at every boot, not once (§2.2).
3. Refusal wording that named a retired key now names *the test channel (shadow_channel_id)* — posts,
   stickies, questions, polls, personal bests; the `/settings` help for `shadow_channel_id` starts *the
   test channel:*.
4. Tests that proved "a feature's own home wins" were re-pointed to prove the feature rehearses in the
   test channel; `tests/test_shadow.py` now proves a stored retired row is never read and that no helper
   takes `feature`.
5. `points_shadow_channel_id` was retired here although only p2/p4k were ticked — the brief named it
   (no reader since v242).
6. Not touched: `birthday_mode` / `golive_mode` help (h1/h2 belong to another build); `switch-audit`
   kept as the dated snapshot it is.

## 6. What was verified on the local mock (fresh, port 8811, Chrome)

- Settings page: one **Test channel** row; none of the eight retired keys or their old labels;
  `structure_backup_shadow_channel_id` still there.
- Posts page *Settings and logs ▸ Settings*: `posts_mode`, `shadow_channel_id` (Test channel),
  `posts_panel_minutes`, `posts_import_style`, `posts_untitled_title`, `posts_log_level` — no rehearsal
  key of its own.
- With the test channel set to #welcome-test (guard off): Post to test on a post → *Sent a test copy of
  **Welcome and rules** to #welcome-test…*; on a sticky → *A test copy of the sticky message in
  #blackbloc-logs is in #welcome-test…*; on the weekly question → *A test copy of this week's question is
  in #welcome-test…*.
- The dry run against the fixture — §2.
