# Move damping — a far-off run's move waits until it reads the same again

> 🔨 **2026-10-10 — BUILT on branch `move-damping` (off `main` `8ecbab63`), NOT merged, NOT deployed.** Schema stays **94** (four nullable columns through `ADDED_COLUMNS`), keys **1208 → 1210**, one new log kind. Deviations and *What was NOT verified* at the foot.

> **Audience:** the conductor (merge + deploy), reviewers, and the next session touching the schedule read, the stream re-time or anything that prints a run's start. **Status:** TRACKED.
> **Last verified: 2026-10-10 ~19:5x Phoenix** — by the build's own gate on the branch (ruff, the hermetic suite, the mock check). ⚠️ Nothing met live Discord, the live database or the live Fastest Furs feed.

🔴 **Read this before the deploy: at the default `marathon_move_damping_reads` = 2 the hour that prompted this build is NOT quieter.** The live cadence for Fastest Furs is one read a minute (`marathon_live_poll_minutes`), and the two wrong values stood **3 reads** (00:04, 00:05, 00:06Z) and **2 reads** (01:03, 01:04Z) before they were corrected. Replayed minute by minute through the real read path (`test_read_every_minute_the_hour_as_it_stood_is_quiet_only_from_four_reads`):

| `marathon_move_damping_reads` | Edits of the public reminder | `marathon.member_run_moved` rows |
|---|---|---|
| 2 (default, as decided) | **4** (each one minute later than on the day) | **4** |
| 3 | 3 | 3 |
| 4 | **2** | **1** |

The decision below fixes the default at 2 and was not widened; the key is on the Settings page. The brief's own replay (wrong value one read, corrected the next) is quiet at 2 and is tested as asked.

## The ask and the decision, verbatim

The diagnosis this answers: [`marathon-fastestfurs-design.md`](marathon-fastestfurs-design.md) ▸ *The back-and-forth hour (2026-10-11)*.

**Why (the brief).** A source's live correction can itself be corrected minutes later. Measured 2026-10-11: the Fastest Furs organisers wrote two `actualDuration` values wrong and fixed each within 3 minutes; reading every minute, the bot published both — run 63 (a BaF runner, ~14 hours away) moved −64, +60, +92, −50 minutes and the PUBLIC 24-hour reminder in #upcoming-events was edited four times, with four `marathon.member_run_moved` log rows.

**The decision (owner, 2026-10-10 19:1x: "Do what you suggest" to this exact proposal).** Damping. A move of a run that is far enough away must read the same on N consecutive reads before anything PUBLIC follows it.

1. Two settings keys: `marathon_move_damping_minutes` (int, default **60**; 0 = damping off = today's behaviour) — a run whose start (both its stored start and the newly read one) is MORE than this many minutes away is damped; a run inside the window is NEVER damped, a late change close to start goes out at once. `marathon_move_damping_reads` (int, default **2**, min 2) — how many consecutive reads must agree on the new time before it is published.
2. What updates AT ONCE, undamped: the stored schedule (`scheduled_at`, `ends_at`), the Marathon tracker page / API, `marathon.fetched` / `marathon.schedule_changed` / `marathon.retimed` rows. The schedule in the database is always what the source last said.
3. What WAITS for the move to hold: every public or member-facing consequence of the move for that run — the edit of an already-posted public reminder (and thread copy), the re-arming / re-scheduling of reminder marks, the `marathon.member_run_moved` log row, and any runner post / highlight / pinned board line that prints the run's time publicly, each damped the same way through ONE helper.
4. Per run, remember the time last PUBLISHED and a pending candidate with a count. A flip that reverses within N reads publishes nothing. When a run crosses INTO the near window with a pending candidate, publish at once. A reminder mark that comes due while a move is pending fires on the STORED (latest) time, never skipped or doubled.
5. Staff moves are never damped (Set start / Shift the day, Started now / Finished now, Back to the sheet). Stream-confirmed starts are never damped either.
6. Applies to every source. Existing rows on first boot: `published_at` NULL means "published = stored" (no burst of edits at deploy).
7. Log: one routine kind `marathon.move_held` when a candidate is first held and nothing when it lapses.
8. NOT in scope: treating `actualDuration` 0 as unfinished (the owner declined it; the v217 reading stays).

## What is stored

Four columns on `marathon_runs`, all NULL on every row that was there before (`ADDED_COLUMNS`; `SCHEMA_VERSION` stays 94, the `staff_start_*` precedent):

| Column | What it is |
|---|---|
| `published_at` | the start public posts still say, while it differs from `scheduled_at`. NULL = they say `scheduled_at` |
| `published_ends_at` | the end that goes with it (a run's own event shows both) |
| `pending_at` | the candidate being counted: the `scheduled_at` the last damped write stored |
| `pending_reads` | how many reads in a row have agreed on it |

None of the four is in any API payload (the routes list their fields).

## The design as built

**Two modules, one rule.** `black_bloc/marathon_damping.py` is the pure half (what a row shows, whether it is far, what one pass does: `step`); `black_bloc/cogs/content/marathon_damping.py` is the half that writes (`written`, `settle`, `publish`, `let_lapse`, `hold`). Nothing else decides.

**At a write.** The two places a schedule read stores a start — `Marathons._write_plan` and `signals.retime` — ask `damping.written(bot, guild_id, row, new_start, now, because=…)` and store what it answers with the new start:

| The write | Answer |
|---|---|
| a read (`because="schedule_read"`), the run upcoming, the start public posts say AND the new start both more than `marathon_move_damping_minutes` away | **held**: `published_at` keeps what was published (the old `scheduled_at` the first time), `pending_at` = the new start, `pending_reads` = 0 unless the candidate is unchanged; the re-arm and the `member_run_moved` row are skipped |
| anything else while a move was waiting (staff, the stream, a read that lands inside the window, the key at 0) | **let go**: the four columns are cleared in the same UPDATE and the move is measured from the PUBLISHED start (`marathon_move_minutes` decides the re-arm and the row, `from` = published) |
| anything else, nothing waiting | exactly the path before this build |

**At a read.** `Marathons.apply` calls `damping.settle(read=True)` after the write and the re-time, on every successful read, changed or not. For each run with `published_at` set (`md.step`):

1. no longer upcoming, or the stored start equals the published one → **clear** (nothing is said; marks skipped as late while the wrong start stood are due again, `mrem.run_fields(…, EDIT)`);
2. the published or the stored start is inside the window, or the key is 0 → **publish**;
3. the stored start is not the candidate that was counted (someone else wrote it) → **publish**;
4. else `pending_reads + 1`: at `marathon_move_damping_reads` → **publish**, below it → store the count, and on the first count log `marathon.move_held`.

**Publish** (`damping.publish`) is the move path that already existed, run against published → stored: if they differ by `marathon_move_minutes` or more the marks are re-armed (`marathon_reminder_on_move` as before) and ONE `marathon.member_run_moved` row per member says `from` = published, `to` = stored; the four columns are cleared either way. The posts then follow by the paths that already edit them (next section).

**At a tick.** `Marathons.follow` calls `damping.settle(read=False)` first, every minute: steps 1–3 only, never the count. That is what publishes a run that crosses into the window between reads, and what lets go of a start somebody else moved.

**What a read is.** One successful `Marathons.apply` — the poll loop's read at whatever cadence the marathon is on (1 minute live for a source that writes actuals, `marathon_poll_minutes` near, `marathon_far_poll_hours` far) and staff's *Read now*. A failed read counts nothing.

## The surfaces that print a run's start, and which are damped

Measured by `grep -n "scheduled_at\|stamp_of\|run_fields(" black_bloc` on the branch. The one helper is `md.shown_start(row)` (`published_at` while a move waits on an upcoming run, else `scheduled_at`); `mt.run_fields` reads it, so every template that prints `{when}` / `{relative}` / `{in}` is damped in one place.

| Surface | Where the start comes from | Damped |
|---|---|---|
| Public reminder (post + edit in place) | `mt.run_fields` via `reminder_text`; `sync_reminders` | ✅ |
| Staff-thread reminder copy (post + edit) | `mt.run_fields` via `Marathons.reminder_words` | ✅ |
| Reminder marks re-armed after a move | `mrem.run_fields` at `_write_plan` / `retime` / `publish` | ✅ (held with the move) |
| `marathon.member_run_moved` | `_write_plan` / `publish` | ✅ |
| Host block heads-up (post + edit) | `mhh.view_row(block)` → `mt.run_fields`; marks via `mhh.rearmed` | ✅ (`repost` re-arms in `edit` mode while the block's first run waits) |
| A run's own post in the thread | `mrp.fields_of` → `mt.run_fields` | ✅ |
| Pinned board lines | `mt.board_text` → `mt.run_fields` | ✅ |
| Public highlight | `mrp.fields_of` → `mt.run_fields` | ✅ |
| A run's own event (events page + Discord scheduled event) | `marathon_events.run_fields` / `redate_run_event` → `md.shown_start` / `md.shown_end` | ✅ |
| `from` / `to` / `at` on `marathon.reminder_edited` and the stored copies | `md.shown_start` | ✅ (they say what the post said) |
| Stored schedule, `GET /api/marathons/…`, the Marathon tracker page | `scheduled_at` | ❌ by the decision (item 2) |
| `marathon.fetched` / `schedule_changed` / `retimed`, `previous_scheduled_at`, `moved_at` | the read | ❌ by the decision |
| When a reminder mark is DUE (`mt.due_marks`, `mhh.due`) | `scheduled_at` | ❌ by the decision (item 4) |
| Going live / done by the clock (`advance`) | `scheduled_at` | ❌ (a state, not a post; such a run is inside the window) |
| The marathon's own event and its spotlight window | the marathon's `starts_at` / `ends_at` span | ❌ Deviation 3 |
| The BaF day event | `sheet_at` of the day's runs | ❌ Deviation 3 |
| Ephemeral panels a person opens (`next_line`, `build_run`, `marathon_people`, the Set start picker) | `scheduled_at` | ❌ Deviation 4 |

## The keys (2, Marathons group: registry + help + mock row + label)

| Key | Type | Default | Range |
|---|---|---|---|
| `marathon_move_damping_minutes` | int | **60** | 0–1440; 0 never waits |
| `marathon_move_damping_reads` | int | **2** | 2–10 |

## The log kind

| Kind | Level | When | Details |
|---|---|---|---|
| `marathon.move_held` | routine | the first read that holds a candidate, for a run of ours whose candidate differs from the published start by `marathon_move_minutes` or more | `marathon_id` `run_id` `game` `published` `candidate` `reads_needed` |

Nothing is logged when a held move lapses or is published (a publish that counts as a move is the `member_run_moved` row).

## Deviations

1. **A mark that comes due while a move waits is posted saying the PUBLISHED start.** It fires at the moment the stored start makes it due (never skipped, never doubled — `test_a_mark_due_by_the_stored_start_fires_once_while_the_move_waits`), but its words go through the same helper as every other post, so it does not announce a start that has not held; if the move holds it is edited once at the publish. The alternative (post the stored start) would put the unconfirmed time in a brand-new public post and have the next minute's edit pass rewrite it.
2. **`marathon.move_held` is not logged for a small move or a run that is not ours.** A Fastest Furs day shifts every later run by seconds to minutes each time a run finishes; a row per run per finish would flood the marathon's log thread. Small moves are still held and counted (`test_a_move_under_the_moved_threshold_waits_too_and_leaves_no_held_row`).
3. **Three marathon-level consequences are NOT damped:** the marathon's own event re-date (`redate_event`), its spotlight window (`sync_window`) and the BaF day event. They follow the marathon's span or the day's `sheet_at` values, not one run's published start, and damping them means a published copy of the span — a deeper change than this build. A wrong last-run length still re-dates the marathon event's end twice.
4. **Ephemeral panels show the stored start.** They are read at the press by one person, like the tracker page.
5. **A staff action that travels as a read waits like a read.** *Read now* and anything else that ends in `cog.refresh` is `because="schedule_read"`; pressing *Read now* again is the second read. Only the moves named in the decision (Set start, Shift the day, Started now, Finished now, Reset, Back to the sheet) and `because="stream"` / `"early_start"` publish at once.
6. **Far marathons lag by one read cycle.** "N reads" at the far cadence (`marathon_far_poll_hours`, 24) means a board line or a run's own post of a marathon weeks away follows a real schedule change a day later at the default. Reminders are not affected until a mark is near.
7. **For a schedule Black Bloc keeps the clock for, a far-off held move is measured net.** Before, a sheet change of `marathon_move_minutes` logged `member_run_moved` from the stored start to the sheet's even when the re-time put the run somewhere else in the same read. While damped the row is written at the publish, from the published start to where the run really ended up; a sheet change the clock undoes in the same read now says nothing. With the key at 0 the old rows come back exactly.
8. **Step 3 (someone else moved it) also logs `member_run_moved`** when the published start moved by the threshold. The named staff paths clear the wait themselves and never reach it; it is the net for a writer this build did not know about.
9. **Three existing tests changed.** `test_a_whole_day_that_shifts_is_one_edit_per_post_ten_a_minute_soonest_first` now reads the shifted day twice (and asserts nothing is edited after the first); `test_a_deleted_host_heads_up_is_logged_once_and_never_posted_again` and `test_repost_posts_a_host_heads_up_again_and_edits_nothing` set `marathon_move_damping_minutes` to 0 — they are about a lost message and `repost`, with a block a day away.
10. **`published_ends_at` is a fourth column** beyond the three suggested, because a run's own event prints the end.

## What was NOT verified

1. ⚠️ **Nothing met live Discord**: no real reminder was held or edited, no scheduled event re-dated.
2. ⚠️ **The default of 2 reads against the live feed.** The table at the top is a replay through the real read path of the times in the diagnosis (themselves partly reconstructed); no live Fastest Furs read was damped.
3. The first boot against the live database (rows with four NULL columns editing nothing) is tested from a file without the columns and from fresh rows, not on Fly.
4. The two Settings rows in a browser (the mock answered the payload; nothing drew it).
5. A rehearsal (`marathon_mode = shadow`) with a move waiting: the edit path is the one `sync_reminders` already had; no test here drives it in shadow.
6. `marathon_reminder_on_move = repost` together with a held move on a RUN (the host-block case is tested; the run case goes through the unchanged `mrem.run_fields` at the publish).
7. The organisers' sheet laid over a marathon (`marathon_overlay`) with a move waiting: it re-times through `signals.retime`, which is tested without the overlay.
