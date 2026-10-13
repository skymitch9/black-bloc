# Stale archive — an unreadable marathon is archived, and tried again when its feed lists it

> 🔨 **2026-10-12 — BUILT on branch `stale-archive` (off `main` `8dd38d16`), NOT merged, NOT deployed.** Schema stays **94** (one nullable column through `ADDED_COLUMNS`), keys **1210 → 1213**, two new IMPORTANT log kinds. Deviations and *What was NOT verified* at the foot.

> **Audience:** the conductor (merge + deploy), reviewers, and the next session touching the schedule read, the archive, Restore or the feed poll. **Status:** TRACKED.
> **Last verified: 2026-10-12 ~22:4x Phoenix** — by the build's own gate on the branch (ruff, the hermetic suite, the mock check, each rule switched off in turn to see its test fail). ⚠️ Nothing met live Discord, the live database, Fly or a live schedule source; nothing was drawn in a browser. Secret NAMES only (none here).

## The ask and the decision, verbatim

Owner, 2026-10-12 22:0x Phoenix: *"what do we do about a stale marathon"*, then *"i think we check a stale marathon 3 times and then archive. if it pops back up on a new scan then we try again"*.

The conductor pointed out that read cadence depends on how near a marathon is — three failed reads is about three days for a far-off marathon and about three minutes for one that is on now — and recommended the archive need both a failure count and a minimum time unreadable. Owner, 22:2x: *"do your suggest"*.

## What happened before

A failed schedule read (`Marathons._failed`) kept every run, added one to `fetch_failures` (not when the source said *not published yet*), logged `marathon.fetch_failed` and, at exactly the third failure in a row, `marathon.schedule_stale` (IMPORTANT). After that nothing more ever happened: the marathon stayed on the live list reading *could not be read since …*. Live example on the day: marathon 17 "Speed Stuff at InfernaLAN 2026", `oengus.io answered 401`, 3 failures.

The feed poll already treated an archived marathon as known (`marathons_by_ref` reads the live table and the archive in one query, leaving out only `archived_why = 'removed'`): **it skipped it — never re-added it, never read it, never restored it.** That part is unchanged; what is new is the one trial read below.

## The rule

After the minute tick reads a marathon and the read fails **and is counted**, the marathon is archived when both hold:

1. `fetch_failures >= marathon_stale_archive_reads` (default **3**, 0–20; **0 never archives**), and
2. at least `marathon_stale_archive_hours` (default **24**, 0–720; 0 = the reads alone) have passed since `marathons.stale_clock_at`.

Never archived by this rule: a paused marathon (it is not read at all), an ignored one, and any read the source answered *not published yet* (it is not counted, so the rule is not asked).

`marathon.schedule_stale` still fires at the third failure, as before.

### The clock — `marathons.stale_clock_at`

`last_fetched_at` is overwritten by every failed read, so it cannot say when the schedule last answered. One nullable column holds the start of the hours clock:

| When | What is written |
|---|---|
| a read that worked (`Marathons.apply`) | the read's time |
| the source answered *not published yet* | the read's time — the source is reachable and said something definite |
| a counted failure while the column is empty | the read's time: the first failure that can be dated |
| a counted failure while it is set | nothing — the clock keeps running |
| Restore (any archived marathon) | the restore's time; a stale one also gets `fetch_failures = 0` |
| Resume it | the resume's time |

**A row from before the deploy has NULL**, and NULL never archives. Marathon 17 (3 failures already) gets its clock started by its first failed read after the deploy and is archived by the first failed read at least 24 hours after that. `added_at` was not used as the start: it would have archived marathon 17 at the first tick after the deploy on a time that says nothing about when its schedule stopped answering.

## The archive

`cogs/content/marathon_stale.archive_if_stale` calls **`marathon_archive.archive_held`** — the function the **Archive it** button, the site route and the ended sweep all go through — with `why = "stale"`, under the marathon's lock the tick already holds. So the linked event and run events are called off, the ping windows dropped, the board unpinned, the thread controls and the inbox message redrawn, and `marathon.archived` logged, exactly as a staff archive does.

**The mark is the existing `marathons_archive.archived_why` column, with a fourth value `stale`** beside `ended`, `staff`, `removed` (`marathon_archive.WHYS`). No new archive column. The reason is kept: `last_error` travels with the row.

Log: **`marathon.stale_archived`** (IMPORTANT) — `marathon_id`, `name`, `reason`, `failures`, `unreadable_since`, `hours`. It is written just before the rows move, while the marathon is still on the live list, so a tracked marathon's row lands in its log thread, where `marathon.schedule_stale` lands (`log_threads.row_of` reads the live table only).

## "If it pops back up on a new scan then we try again"

In `marathon_feeds.run_check`, every event the feed's list names whose `source` + `source_ref` is an archived marathon marked `stale` (and has no live marathon on the same ref) gets **one read of its schedule per check, while it is still archived** (`cogs/content/marathon_stale.try_again`).

- The read works → `restore_marathon` (the existing Restore), the marathon is put back **active** (Restore alone leaves it paused), the read is applied (`Marathons.take`, the same code a tick read runs), which sets `fetch_failures` to 0 and restarts the clock; the mark is gone with the archive row. Logged: `marathon.restored` (the Restore path's own row) and **`marathon.stale_restored`** (IMPORTANT) — `marathon_id`, `name`, `runs`.
- The read fails, or answers *not published yet*, or Restore refuses (the link is taken by another marathon) → it stays archived. **No log row of its own**: the check's routine `marathon.feed_checked` row carries `stale_tried` and `stale_restored` counts.

A feed that keeps listing an unreadable event therefore costs one read per check (`marathon_feed_hours`) and nothing else: no restore, no archive, no IMPORTANT row (tested over three polls).

A marathon staff archived by hand is never read or restored by the poll. A stale-archived marathon no feed lists stays archived until staff Restore it.

## Staff final say

Restore on the site or the Discord Archive card works on a stale-archived marathon as on any other. It comes back paused with `fetch_failures = 0` and the clock at the restore, so after Resume the two conditions must be met afresh.

## What staff see

- **Site, Events ▸ Archive:** a stale row carries a small warn-toned state word after its *archived … ago*, and the archived drawer's who-line says the same word instead of *archived by staff*.
- **Discord, Archive card:** the row's why and the Restore pick's description say the word.
- The word is the key **`marathon_archived_stale_word`** (default *could not be read*); the API sends it as `archived_why_word`, a field the archive payload already had. No route shape changed; `stale_clock_at` is not in any payload.

## Keys, columns, kinds

| Kind | Name | Notes |
|---|---|---|
| key | `marathon_stale_archive_reads` | int, 3, 0–20 |
| key | `marathon_stale_archive_hours` | int, 24, 0–720 |
| key | `marathon_archived_stale_word` | text, *could not be read*, no fields |
| column | `marathons.stale_clock_at` | TEXT, nullable; `ADDED_COLUMNS` + the CREATE; the archive twin gains it by the mirror |
| value | `marathons_archive.archived_why = 'stale'` | no new column |
| log kind | `marathon.stale_archived` | IMPORTANT |
| log kind | `marathon.stale_restored` | IMPORTANT |

Each key has its registry entry, help, range, mock row, contract min/max and label.

## Deviations from the brief

1. **The mark is `archived_why = 'stale'`, not a new nullable column.** The archive table already records why a row moved; a second column saying the same thing would be two homes for one fact.
2. **Three keys, not two.** The stale state word is shown on the site and in Discord, so it is a key (owner rule: every shown word is editable).
3. **The stored time is a clock start, not strictly "the last good read".** It is also written by an unpublished answer, by Restore and by Resume, and by the first counted failure when empty (table above). Each is a case where "hours since the last good read" would archive on a burst of failures that says nothing about a day of silence.
4. **Only the tick's read archives.** A staff *Read now* that fails counts the failure and archives nothing; the next failed tick read decides. Staff looking at a marathon should not have it leave under their hand.
5. **A bot restore un-pauses.** The existing Restore brings a marathon back paused; a paused marathon is never read, which would make "try again" a dead end. The bot sets `active` back to what the archived row held (always 1: the rule archives only active marathons).
6. **A failed trial read writes no row of its own.** The brief allowed one routine row per poll; the counts on `marathon.feed_checked` say the same with no new row.
7. **`marathon.archived` is also logged** (IMPORTANT, with `archived_why: stale`) because the archive goes through the one path. One stale archive is two IMPORTANT rows: the thread's `marathon.stale_archived` and the channel's `marathon.archived`.
8. **`Marathons.refresh` was split**: the part after the fetch is `Marathons.take`, so the trial read's runs are applied without reading the source a second time.

## Tests, and how each was seen failing

New: `tests/test_marathon_stale.py` (11), `tests/cogs/content/test_marathon_stale.py` (19), one each in `tests/storage/test_db.py`, `tests/test_settings_store.py`, `tests/api/tools/test_marathons.py`, and the stale asserts added to the who-moved-it test in `site/mock/marathon-words.test.mjs`.

Written after the code. Each rule was then switched off in the source and the tests re-run (measured 2026-10-12): the archive call removed → 11 fail; hours ignored → 7; reads ignored → 6; a NULL clock archiving → 1; an uncounted (unpublished) failure archiving → 1; restoring without a working read → 2; every archived row tried / the mark ignored → 1 each; Restore keeping count and clock → 4; the clock never started on a failure → 4; paused/ignored not exempt → 3; a good read not stamping the clock → 7; a bot restore left paused → 1; Resume keeping the old clock → 1; the word not read from its key → 2; the `ADDED_COLUMNS` row removed → the migration test fails. None was run against `main` itself.

## What was NOT verified

- Anything live: Discord (the inbox message, the thread controls, the log thread), Fly, the live database, marathon 17, a real Oengus 401.
- The site in a browser: the state word on the Archive row and in the drawer were checked by `marathon-words.test.mjs` and `check.mjs` only, never drawn.
- That marathon 17 has a feed that lists it. If none does, it stays archived until staff Restore it.
- What a bot restore does to a marathon whose Discord event was called off by the stale archive: the read's own `event_follows` / `sync_runs` run as on any read; no test covers an event being made again.
- The Discord Archive card in a real client.
