# Marathon category track — the stream's Twitch category as a third signal, and Black Bloc keeping the clock

> **Audience:** the conductor, reviewers and future sessions touching marathon live-tracking. **Status:** TRACKED ·
> 🔨 **BUILT on branch `marathon-category-track`** (off `main` `97f0f1bd`; commits `6a0c74d8` core + cog + API + tests,
> `c567f987` site + mock + contract, `fe5d8e58` the Discord view's test, `f42cb3cb` tidy, and the docs commit) —
> **NOT merged, NOT deployed, nothing has met Discord, Twitch or Fly.** Schema **80 → 81**, registry keys
> **695 → 697**, routes **+1** (`check.mjs`: *22 pages, 283 routes*). **Last verified: 2026-09-28** — against the suite
> (fake Helix, no network) and the mock; ⚠️ **no live Twitch call was made** (see *What was NOT verified*). Secret NAMES
> only: `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET` (the go-live cog's existing app token — nothing new).

## The ask, verbatim

Owner, 2026-09-28 14:2x–14:3x:

- *"the times are all wrong, we need to take the times of each run and progress the clock ourself, lets also add a
  tracker for twitch activity to see if the game matches the category to be douvle certain. also if the game doesnt
  have a twitch category it'll fall into retro most likely"*
- *"also track title of the twitch stream"*

⏰ Games Done Queer (GDQueer, a Hotfix show on the GDQ channel) starts **Sat 2026-10-03 10:00 Phoenix** (17:00Z).

## The design, as built

### 1. Title AND category on the same poll

The spotlight sweep (`cogs/content/spotlight.py`, every `SPOTLIGHT_POLL_MINUTES`, one Helix `get_streams` for every
spotlit channel — **no second Twitch poller**) already kept the stream's `title` and `game` (the category NAME) on
the open `spotlight_sessions` row. It now also keeps **`game_id`** (schema 81): written by `start_session`, refreshed by
`_refresh` → `refresh_session_info` whenever the title, the game or the id changes. A game change that arrives with no
id (a presence-sourced update) clears the stored id rather than leaving the old game's id beside the new name.

### 2. Signal 3 — the category

**Each run's category is looked up ONCE** (`cogs/content/marathon_signals.py:resolve_categories`, on the marathon
minute tick, for a NEAR marathon that has a channel, while `marathon_category_confirms` is on): through the go-live
cog's `TwitchClient` (one app token), `games_named` (Helix `games?name=`, up to 100 names a call) for every name the
run carries (`twitch_game` from the GDQ tracker, then `game`, then `display_name`), then — for a run still not found
— `search_categories` per name, accepting ONLY a result whose name is the run's own once punctuation and capitals are
set aside (`marathon_signals.found_in`). The answer is kept on the run: `twitch_game_id`, `twitch_category`,
`twitch_looked_at` (all NULL until looked up; a looked-up run with no id is **"Twitch has no category for this"**).
25 runs a tick; a Helix failure logs `marathon.category_lookup_failed` (IMPORTANT by its suffix) and waits
`LOOK_AGAIN` (30 min) before asking again; a sheet read that changes a run's game clears its lookup so it is asked
again. The log of a successful pass is `marathon.categories_found` (`found`, `none`).

**Matching** (`marathon_signals.category_matches`, pure): for every open run within `TITLE_REACH` (12 h) of its
start —

- the stream's category **id** equals the run's `twitch_game_id` → a **direct** hit; a run looked up with a
  DIFFERENT id is never a hit, whatever the names say;
- a run not looked up yet (no Helix, or not reached) matches by **name**: normalised equality or whole-word
  containment either way between the category name and the run's `game` / `display_name` / `twitch_game` /
  `twitch_category` (the GDQ tracker's `twitch_name` match that used to live inside the title signal is here now);
- **the Retro rule:** when the stream's category name equals **`marathon_retro_category`** (text, default `Retro`,
  capitals ignored), it stands ONLY for runs Twitch has no category for (looked up, none found) — a Retro hit, not
  direct. A run WITH its own category never matches Retro.

### 3. The decision

`marathon_signals.decide` (pure), called from `Marathons.advance` through `signals.verdict_of`:

| Title says | Category says | Goes live | `live_because` |
|---|---|---|---|
| run A | A is among its matches | A | `title+category` — **certain** |
| run A | nothing | A | `title` |
| nothing | run B | B | `category` |
| run A | run B, direct | **B** | `category`, and `marathon.signals_disagree` (routine) |
| run A | run B, Retro only | **A** | `title`, and `marathon.signals_disagree` |

Among several category matches the best is: direct over Retro, then the run **already live** (so a game played twice
in a row does not hand over at the midpoint), then the nearest start. `signals_disagree` carries the title, the
category and its id, both runs and what was trusted, and is logged **once per pair of runs** per process (the tick is
every minute). A run already live by the **schedule's clock** that the stream then confirms is re-recorded
(`Change.confirmed`) — its `live_because` becomes the signal and the clock is anchored then; a run live by one signal
that the other then agrees with is upgraded to `title+category` (anchor kept). Every existing Signal-2 behaviour holds
for every signal: earlier upcoming runs go `done` quietly, a skipped run of ours logs `marathon.run_skipped`
(IMPORTANT), `marathon_late_grace_minutes` waits while the stream is watched, held (staff) runs are never moved, and
`marathon.run_live` carries `because`. **`marathon_category_confirms`** (bool, default on) sits beside
`marathon_title_confirms`; with both off the schedule decides alone.

**The mark:** the marathon drawer's run row (`site/public/assets/marathons-section.js`, `slotRow`) shows a small
**`certain`** badge (hover: *The stream's title and its Twitch category both name this run.*) — page constants
`CERTAIN_NOTE` / `CERTAIN_HELP`, staff-facing words. The API's run row carries `certain`, and
`live_because_word` gains *the stream's Twitch category* / *the stream's title and Twitch category*.

### 4. Black Bloc keeps the clock

**Per source** — `marathon_sources.RETIMES_ITSELF` / `retimes_itself(source)`: every tracker/site that re-times its
own later runs is `True`; **`gdq_hotfix` is `False`** (the sheet's *Show Start* is the show's, and the estimates never
move). Unknown sources count as re-timing themselves.

**The columns** (schema 81, `marathon_runs`): `sheet_at` / `sheet_ends_at` — the SOURCE's own times, written on every
insert and every sheet-changing read (backfilled from `scheduled_at` / `ends_at` on an old file);
`actual_started_at` / `actual_ended_at` — anchors. **`scheduled_at` / `ends_at` are the times Black Bloc believes**, so
every downstream reader — reminders and their marks, the board, *BaF next* / *My runs*, the title reach, the grace,
the drawer — uses the kept clock with no change of its own.

**The anchor:** a run that goes `live` by `title`, `category` or `title+category` gets `actual_started_at` = the tick's
`now` (the moment of detection). **The re-timing** (`marathon_signals.retimed`, pure): the runs are split into
**chains** — runs the sheet puts back to back (next sheet start = previous sheet end ± 1 min — ⚠️ **since 2026-10-03,
0 to 30 minutes after, and every later run also waits `marathon_setup_minutes`**: `marathon-hotfix-design.md` ▸
*Follow-up 2026-10-03 — setup buffer*); a gap, such as the
next show-day, starts a new chain. Walking a chain in sheet order: before the first anchor a run keeps the sheet's
times; an anchored run starts at its actual start; every later run starts where the previous one should end (its
start + its estimate, or its `actual_ended_at`). `Marathons.retime` writes only the runs whose times differ, re-arms
a run's reminder marks when it moved by at least `marathon_move_minutes` (the existing move rule), and logs
`marathon.retimed` (routine; `runs`, `because`, the first run's from/to). Runs for a source that re-times itself are
never touched (the anchor is still recorded — it is a fact — but nothing moves).

**The sheet read never wipes it:** `mt.diff` compares a run's new start with `sheet_at` (not the kept time), so a
re-timed run is not "moved"; the write puts the sheet's times into both pairs and then `retime` runs again from the
anchors (`because: schedule_read`). An unchanged sheet (same hash) writes nothing at all.

**Staff final say** — every move re-times: **Mark it live** anchors at that moment; **Mark done** on a live run ends
it at that moment (`actual_ended_at`, so the next run starts then); **Mark it upcoming** clears the run's anchors.
**Back to the sheet's times** puts EVERY run of the marathon back on the sheet's own times and clears every anchor
(`marathon_signals.on_the_sheet` → `cogs/content/marathon_signals.sheet_times`, under the marathon's lock, logs
`marathon.sheet_times`, refreshes the board); it refuses in words when there is nothing to undo (`not_retimed`).
The stream re-times again only when it next shows a run STARTING. Doors: `POST /api/marathons/{id}/sheet-times`
(the drawer's move bar, drawn while `retimed_runs` > 0) and the Discord **`/event` ▸ Marathons ▸ a marathon ▸
Schedule…** view (a *Times: N run(s) re-timed from the stream* line and the button, while any run is re-timed).

### 5. Locking

Everything above runs inside the marathon tick, which runs under the cog's `Reconciler` (checklist 37) and the
per-marathon `cog.lock(id)`; the staff moves take the same per-marathon lock. Proven by
`test_two_ticks_at_once_flip_and_re_time_exactly_once` (three reconciler runs gathered, one `marathon.retimed`).

### 6. Nothing pings

No ping key was turned on and no mention was added. A run of ours going live by category is shouted exactly as by
title (`marathon_live_pings` still decides, default off) — proven with no role mention in any post.

## Keys, schema, routes, log kinds — before → after

| | Before | After |
|---|---|---|
| Schema | 80 | **81**: `spotlight_sessions.game_id`; `marathon_runs.sheet_at`, `sheet_ends_at` (backfilled), `actual_started_at`, `actual_ended_at`, `twitch_game_id`, `twitch_category`, `twitch_looked_at` (the archive twin mirrors them at boot) |
| Registry keys | 695 | **697**: `marathon_category_confirms` (bool, on), `marathon_retro_category` (text, `Retro`, 1–60 chars, `checked_retro`) — Settings page, `/settings` key card, mock rows, labels, help. `marathon_title_confirms`'s help now says *title* only |
| Routes | 282 (`check.mjs`) | **283**: `POST /api/marathons/{id}/sheet-times`. `GET /api/marathons/{id}` gains `retimed_runs`, `keeps_clock`; each run row gains `sheet_at`, `retimed`, `actual_started_at`, `certain`, `twitch_category`, `no_category` |
| Log kinds | — | routine `marathon.retimed`, `marathon.sheet_times` (`web.` from the site), `marathon.signals_disagree`, `marathon.categories_found`; IMPORTANT (suffix) `marathon.category_lookup_failed` |
| Helix client | `get_streams`, `get_users`, `get_games` | + `games_named(names)`, `search_categories(query)` |

## The GDQueer example (the fixture `tests/fixtures/marathon/gdq_hotfix_sheet.csv`, times in Phoenix)

The sheet: Spyro Reignited Trilogy 10:00 (1:08), Hamtaro: Ham-Hams Unite! 11:08 (0:52), Kirby's Dream Land 12:00
(0:15), WarioWare: Touched! 12:15 … At **10:10** the channel is in *Just Chatting*: nothing is live (Spyro waits the
grace). At **10:20** the category is *Spyro Reignited Trilogy*: Spyro goes **live by category**, anchored at 10:20,
and the day re-times — **Spyro 10:20–11:28, Hamtaro 11:28–12:20** (= Spyro's actual start + 1:08), **Kirby 12:20**,
WarioWare 12:35, … 13 runs of Saturday moved, Sunday's first (*Wii Fit U*) stays **Sun 10:00** (a new chain). The
drawer shows Hamtaro at 11:28 *· sheet said 11:08*. (`test_spyro_seen_20_minutes_late_by_its_category_re_times_hamtaro_to_its_start_plus_1_08`.)

**The Retro rule's test** (`test_a_run_with_no_category_is_matched_by_the_retro_category_and_one_with_its_own_is_not`):
the fake Helix knows Spyro, Hamtaro, Kirby, WarioWare and Kilaflow; Denshattack!, Bombun and the rest have none. At
Bombun's sheet time + 2 min the channel is in *Retro* (id 27284): **Bombun** goes live by category (the nearest run
with no category), Denshattack! before it goes done, **Kilaflow — which has its own category — stays upcoming** and is
re-timed to Bombun's start + 0:46.

## Deviations

1. ⚠️ **`scheduled_at` holds the kept clock; the SHEET's times moved to new columns (`sheet_at`, `sheet_ends_at`).**
   The brief said to keep an `actual_started_at` / re-timed column distinct from the sheet's `scheduled_at`. The
   distinction is kept, the naming is inverted: every downstream reader (reminders, marks, board, up next, advance)
   already reads `scheduled_at`, so putting the believed time there means none of them needed a change, and the diff
   compares with `sheet_at`. Old rows are backfilled (`sheet_at = scheduled_at`).
2. ⚠️ **The title signal no longer carries the category.** `mt.title_hit` is called with no game: the old
   "stream category = the run's GDQ `twitch_name`" match is now part of Signal 3. With both keys on (the default)
   nothing a GDQ marathon did before is lost; with `marathon_category_confirms` off, a category-only match no longer
   confirms a run. `marathon_title_confirms`'s help text says so.
3. **The actual start is the moment of detection on the minute tick**, not the session's poll time — up to about six
   minutes after the real start (a five-minute poll, then a one-minute tick). No column records the poll time.
4. **A "day block" is a chain of runs the sheet puts back to back**, not a calendar date — for the Hotfix sheet that
   is exactly the show-day; it also works for any future source with gaps between days.
5. **The schedule's clock going live (after the grace) does not anchor.** Only the stream or staff do; a later title or
   category confirmation of that run anchors then.
6. **Back to the sheet's times is per marathon, not per run**, and works on any source (it clears the anchors a
   self-re-timing source records too).
7. **Shout it now** (which flips an upcoming run live as staff) does not anchor; **Mark it live** does.
8. **Per-run Discord events** (`marathon_event_mode` runs/both) follow the kept clock at the next schedule read
   (`sync_runs` after `apply`), not at every detection.
9. **The lookup's search fallback accepts only a same-name answer**, so a search that returns a near game is never
   taken; without Helix credentials nothing is looked up, the Retro rule cannot fire (no run is known to lack a
   category), and the category matches by name only.
10. **Two Retro runs back to back hand over by the title, the clock's grace, or staff** — the category alone keeps
    pointing at the run already live (that stickiness is what stops a repeated game handing over mid-run).
11. **`marathon.signals_disagree` is deduplicated in memory** per marathon and pair of runs; a restart may log the
    same pair once more.
12. **The mock's GDQueer (marathon 50) seeds Saturday's shape** — Spyro live and certain 20 minutes late, Hamtaro
    and Bombun re-timed — so the drawer and *Back to the sheet's times* can be seen before Saturday; `check.mjs` runs
    the sheet-times route against it (`marathon_retimed_id: '50'`).
13. **The mock re-times on staff moves only** (`marathonRetime`); it has no stream.

## Tests

`tests/test_marathon_signals.py` (new, 19): direct id hit; a looked-up run with another id never matches; names
before a lookup; **Retro stands only for runs with no category** (and not for one with its own, nor a run never looked
up); the Retro name is the setting; done/dropped/far runs never match; certain; title only / category only / none;
disagreeing (direct wins, title beats Retro); the title picks among several category matches; the live run keeps the
category; a clock-live run re-recorded when the stream confirms; the 20-minutes-late chain; staff ending early pulls
runs forward; no anchor → back to the sheet; nothing written when nothing differs; the retimed count and the way
back; `retimes_itself`; `found_in` (exact, same-name search, a near search refused).
`tests/cogs/content/test_marathon_signals.py` (new, 16), all through `cog._reconciler.run(cog.tick_once)` on the
**GDQueer fixture**: looked up once (5 found, 19 none) and not again; a refused lookup logged and retried only after
30 min; **Spyro 20 min late by category → Hamtaro at Spyro's actual start + 1:08**, Sunday untouched; **Retro**;
title only; both → certain; one signal upgraded to certain keeps its anchor; **disagreeing** (direct category trusted,
logged once over two ticks); Retro vs title → title; the key off → no lookup, no category; **a GDQ tracker marathon is
never re-timed** (the anchor is recorded, the next run stays); **a sheet refresh keeps the re-timing** (Kirby's
estimate changed on the sheet: Hamtaro stays 11:28, WarioWare follows the new estimate); **staff clear restores the
sheet's times**, refuses twice, and Mark it live / Mark done / Mark it upcoming each re-time; three reconciler runs at
once re-time exactly once; a run of ours shouted with no ping; the Discord Schedule view's line and button.
Also: `tests/test_twitch.py` +4 (`games_named`, `search_categories`, no call for nothing, failure), 
`tests/cogs/content/test_spotlight.py` +1 (the poll keeps title, game and id; a presence-style game change clears the
id), `tests/storage/test_db.py` +1 (a schema-80 file: backfill, session column, archive twin) and two pins unpinned,
`tests/test_settings_store.py` +1 and the key count, `tests/api/tools/test_marathons.py` +1 (the route, the fields, the
409, `web.marathon.sheet_times`), `tests/api/test_contract.py` (the seed anchors a run so the route answers 200). No
test makes a network call.

## What was NOT verified

1. ⚠️ **No live Twitch.** `games?name=` and `search/categories` are exercised on fakes only: whether Helix matches
   `name` case-insensitively, what the search returns for these 24 games, and **which of GDQueer's games Twitch really
   has a category for** are unknown. The fake's split (5 found / 19 none) is invented for the tests.
2. ⚠️ **Whether GDQ actually streams a no-category game under `Retro`** — the owner's *"most likely"*; if they use
   another category, change `marathon_retro_category`.
3. **Nothing met Discord or Fly**; the schema step was proven on a fresh file and a downgraded schema-80 file, not
   the live volume. The drawer's `certain` badge, the *sheet said* hint and the button were checked in the mock's
   contract (`check.mjs`), not clicked in a browser (no browser use in this build).
4. **That the GDQueer marathon has the GDQ channel as its `spotlight_id`** and that channel is spotlit while it airs —
   Signal 2 and 3 both need the open spotlight session. The Hotfix feed sits on the `gamesdonequick` row
   (`marathon-hotfix-design.md`), so a feed-made GDQueer should carry it; not checked live.

## Live check — Saturday 2026-10-03 (after the deploy)

| When (Phoenix) | Look at | Expect |
|---|---|---|
| Any time before 10:00 | Events ▸ Marathons ▸ **GDQueer** drawer | 24 runs on the sheet's times (Spyro 10:00, Hamtaro 11:08, Kirby 12:00). Action log: one `marathon.categories_found` (how many found / none — the first real answer to *NOT verified* 1); no `category_lookup_failed`. |
| ~09:50–10:30 | Go-live ▸ the GamesDoneQuick channel | The session's title and category follow the stream within ~5 min. |
| When Spyro actually starts | the drawer | Spyro **on now**, `live_because` *the stream's Twitch category* (or *title and Twitch category* + the **certain** badge); Hamtaro's time = Spyro's real start + 1:08, *· sheet said 11:08*; `marathon.retimed` in the log. |
| Each hand-over | the drawer | The new run goes live, the one before goes done; later runs follow the new start. A `marathon.signals_disagree` row means title and category named different runs — read which was trusted. |
| A game with no Twitch category | the drawer | While the channel is in **Retro**, that run is the one on now; a run with its own category is never matched by Retro. |
| If the times look wrong | the drawer ▸ **Back to the sheet's times** (or `/event` ▸ Marathons ▸ GDQueer ▸ Schedule…) | Every run back on the sheet's times; the next run the stream shows starting re-times from there. Mark it live / Mark done also move the clock. |
| Sunday 10:00 | the drawer | Sunday's first run starts from 10:00 (a new chain), whatever Saturday did. |

## The early-start guard — 2026-10-04 (hotfix `early-start-guard`)

**What happened.** On GDQueer day 2 the channel put up *Wii Fit U*'s title and category at 15:40Z as pre-show setup, 80 minutes before its 17:00Z start. The next tick called the run live by title+category, anchored it at 15:41Z and re-timed the day's 11 runs 79 minutes early; a member's run moved from 19:03Z to 17:44Z and its 2-hour reminder went up with the wrong time. Day 1 had the same thing, 7 minutes early.

**The rule.** The stream may not call a show-day's FIRST run live earlier than `marathon_early_start_minutes` (int, 0-240, default 15; 0 = off, the behaviour before) before its planned start (`sheet_at`, else `scheduled_at`). "First" = no run before it in its show-day is live or done; the show-day is `marathon_overlay.chains` (three hours with nothing on starts a new one) for every source, trackers included. While it is held nothing changes and one `marathon.early_match_held` row is written per run (kept in memory, so a restart may write one more). Later runs of a day are never held - a show running ahead is still followed. Staff *mark live* is never held.

**The repair.** Every tick, before the verdict: a run that is live by the stream, opens its show-day, was anchored earlier than that line, and is still before it now, is put back to coming up (`put_back`, the same columns staff *mark upcoming* clears, `live_because` NULL) and the day is re-timed through `retime` (so the overlay's times when it is applied; a tracker is not re-timed, it keeps its own). One `marathon.early_start_undone` row. Nothing is posted: the re-time runs in `edit` mode whatever `marathon_reminder_on_move` says, so a posted mark stays posted and the standing copies are edited by the ordinary sync. Once now is past the line the run is left live.

**Not covered.** A stream set up inside the last N minutes still anchors the day up to N minutes early.
