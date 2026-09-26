# Marathons are archived, never deleted — an archive table for ended marathons, and an expiry that keeps marathon channels

> **Audience:** the build agent (a cloud agent under an Opus 5.5 conductor, per the owner 2026-09-26 14:3x) and reviewers.
> **Status:** TRACKED · 🔨 **BUILT 2026-09-26 on branch `marathon-archive-local` (off `main` `33b9838a`, schema 70, keys 508), NOT merged, NOT deployed** — §B, §C and §D as below, with the numbered Deviations at the foot. Was: 📐 **DESIGN (Fable, 2026-09-26 14:3x Phoenix), NOT built** — queued for the Sunday 2026-09-27 16:00 weekly reset (weekly 89 % at 14:07, the project's dispatch cut-off is 90 %). Branch `marathon-archive`, off `main` at or after `76501919` (v173 live; `marathon-spotlight` MERGED and NOT deployed — schema is **69** on `main`, so this build takes **70**).
> **Last verified: 2026-09-26 (the build)** — by running it: the full suite, `check.mjs` and a headless render against the branch's mock (figures and what was NOT checked at the foot). Before that, **2026-09-26 14:3x** — by reading the code on `main` `76501919`: `black_bloc/storage/db.py` (`marathons` `:1017` with its `ADDED_COLUMNS` `:1195–1207`, `marathon_runs` `:1042`, `marathon_people` `:1073`, `marathon_feeds` `:1087`, `marathon_spotlights` `:1117`, `spotlight_ping_windows` `:929`), `black_bloc/cogs/content/spotlight.py:661` `_expire` (the sweep that DELETES an expired row: `_end` the open session → `drop_fan_role` → `drop_feeds_of_channel` → `delete_channel`), `black_bloc/marathon_spotlight.py` (`is_kept`, `held_by`, `lifted_fields` — the follow build's rule that a marathon never writes `expires_at`), `black_bloc/cogs/content/marathon_feeds.py` (`marathons_by_ref` — the dedupe that must keep seeing archived refs), `site/public/assets/marathons-section.js` (`listSection`, the table, `marathonDrawer`). ⚠️ NOT verified: nothing was run; the live database was not read for this doc (the 13:3x read of the rows is in `TODO.md`). Secret NAMES only.

## The ask, verbatim (owner, 2026-09-26 Phoenix)

- 14:1x, in answer to the finding that a channel row's expiry DELETES the row, its ping role and its feed: *"i think we move marathons to a archive table"*.
- 14:2x, to the suggestion below: *"do the design doc for both then im gonna swap to opus 5.5 as leading model with cloud agents to do the build"*.

The suggestion he accepted (Fable, 14:2x): **(1)** expiry never deletes a marathon channel — a row that carries a feed or a marathon drops back to kept with spotlight off when its date passes; **(2)** ended marathons move whole to an archive table after a grace period, browsable on the site; **(3)** by hand today, SS4C and RGL become *kept* so Monday's sweep deletes nothing. ⚠️ **(3) was NOT done at the time of writing** — the owner had not said yes to it in so many words. It is the first thing the next conductor should put to him (rows 6 `speedstuff4charity` and 7 `retrogaminglivetv` read *until 28 Sep* at 13:3x; the sweep runs on the minute tick, so the loss lands early 2026-09-28 Phoenix).

## A. What is wrong today, named

1. **`_expire` deletes.** `cogs/content/spotlight.py:661`: an expired row loses its open session, its fan role, **its feeds** (`drop_feeds_of_channel`) and then the row itself. Right for a member's temporary spotlight (the shape it was built for); wrong for a marathon channel, which must live forever and only light up during events. Two live rows are on that path (6, 7).
2. **Marathons are kept forever in the live table.** Six rows today; the feeds add one per event found, so the live list, the inbox thread (`marathon-inbox-design.md`) and every "next marathon" query grow without end. There is no history view and no way to tell "done" from "coming" except by dates.
3. **The follow build already refuses to write `expires_at`** for exactly reason 1 (`marathon-spotlight-design.md` Deviation 1). This design makes that refusal unnecessary but keeps it: a marathon still never sets an expiry; it marks `spotlit_by_marathon` and the sweep lifts it.

## B. Expiry keeps a marathon channel (the small half)

In `_expire`, BEFORE anything is dropped: if the row **carries** anything marathon-shaped — a `marathon_feeds` row with this `spotlight_id`, a live `marathons` row with this `spotlight_id`, or `spotlit_by_marathon` set — then instead of the delete path:

- write `spotlight = 0`, `expires_at = NULL`, `starts_at = NULL`, `spotlit_by_marathon = NULL` (the row is now *kept*, spotlight off, exactly what `marathon_spotlight.lifted_fields()` writes — reuse it);
- end the open session as today (`_end`, the same EXPIRED words);
- keep the fan role and the feeds;
- log **`golive.spotlight_kept`** (IMPORTANT, new kind) with `spotlight_id`, `login`, `because = marathon_channel`, and which of the three signals held it;
- answer nothing in Discord (a sweep is silent); the row's *until* word on the site reads *kept* from then on.

A row that carries none of the three still deletes as today — no change for members' spotlights. One helper decides: **`black_bloc/marathon_channels.py:carries_marathons(db, spotlight_id) -> tuple[str, ...]`** (the signals that held), tested pure with fakes. Configurable both ways (checklist 33): key **`golive_expiry_keeps_marathon_channels`** (bool, default **on**; off restores the delete path) in the Go-live registry, with a mock row and a label.

## C. The archive table (the big half)

### C1. Schema 70

```
CREATE TABLE IF NOT EXISTS marathons_archive (
    -- every column of marathons, same names and types, PLUS:
    archived_at   TEXT    NOT NULL,
    archived_by   INTEGER,            -- NULL = the sweep
    archived_why  TEXT    NOT NULL    -- 'ended' | 'staff' | 'removed'
);
CREATE TABLE IF NOT EXISTS marathon_runs_archive     ( -- every column of marathon_runs );
CREATE TABLE IF NOT EXISTS marathon_people_archive   ( -- every column of marathon_people );
CREATE INDEX IF NOT EXISTS marathons_archive_by_guild ON marathons_archive(guild_id, ends_at);
```

The archive tables mirror the live ones column for column so a row moves with `INSERT INTO … SELECT *`-style copies (spell the columns out; `SELECT *` breaks the moment a column is added — checklist 6). ⚠️ Column lists are read from the live table at build time (`PRAGMA table_info`) and asserted equal in a test, so a future `ADDED_COLUMNS` entry on `marathons` fails a test until its archive twin exists — put the twin rule in `db.py` beside `ADDED_COLUMNS` (an `ARCHIVED_TABLES = {"marathons": "marathons_archive", …}` map that the boot uses to add missing columns to the archive too).

`marathon_spotlights` (a runner's spotlight window made from a marathon) and `spotlight_ping_windows` rows with `source = 'marathon'` are **deleted** with the move, not archived — they are effects, already expired by then, and the sweep that lifts them keys on live rows. Say so in the design's Deviations if the build finds one still open.

### C2. When a marathon moves

A marathon is **ended** when `now > ends_at + grace`, where `ends_at` is the marathon's span end (the last run's end, the same span `marathon_spotlight.span_of` uses; a marathon with no runs and no `ends_at` never ends by itself) and grace is the key **`marathon_archive_after_days`** (int, default **7**, 0–365; 0 = the same day). The marathon **tick** (the existing per-minute loop in `cogs/content/marathon.py`, under its lock — checklist 37) moves ended marathons ONE per tick (never a batch that could hold the lock through a long copy): copy the row + its runs + its people into the archive tables inside one transaction, then delete the live rows, then log **`marathon.archived`** (IMPORTANT: `marathon_id`, name, source/ref, runs, BaF count, `archived_why = ended`). Staff can archive early: a **Archive it** move on the drawer and the panel (`archived_why = staff`), with a confirm; and **Remove** (the existing delete) becomes an archive with `archived_why = removed` — nothing about a marathon is deleted any more (the ask). `Remove`'s words change to say *archived*; the feed's ignore list still remembers a removed ref so the feed does not re-add it.

### C3. What keeps working across the move

- **Feed dedupe:** `marathons_by_ref` (feeds cog) must read live AND archive refs, else a feed re-adds an archived event that is still on its list (GDQ's list keeps past events for months; Oengus `open` too). One query over a `UNION`, tested.
- **The next-event suggestion** (`marathon-next-event-design.md`) reads the newest ended marathon of a source to say *after X, the next is Y* — it reads the archive now.
- **Spotlight windows and the follow:** an archived marathon holds nothing; `held_by` / `dimmed_during` read live rows only — assert it.
- **The event link** (`event_id` on the row): the Events row keeps its `marathon` line by reading both tables (one helper `marathon_by_id_any`).
- **The inbox thread** (`marathon-inbox-design.md`): an archived marathon's inbox message is edited to *Archived {when}* and its own thread is archived on Discord (`thread.edit(archived=True)`), not deleted.
- **`/api/marathons/{id}` for an archived id** answers the archived row with `archived: true` and no moves but **Restore** (staff final say: one move copies it back to live with `active = 0`; a restored marathon is paused until staff resume it, so nothing posts by surprise).

### C4. The site

The Marathons section gets an **Archive** shut `foldout` under the table (title *Archive · N*), listing archived marathons newest first: name · source · dates · runs · BaF · *archived {when} by {who}* — one line each, opening the same drawer in a read-only shape (the header, People with the day folds, no Settings, one **Restore** button). `GET /api/marathons/archive?limit=50&offset=0` (paged; the contract lists it). The mock seeds two archived rows (one with a BaF runner) so the foldout and the drawer render. Judge it by the owner's standard: a staff member who has never seen it knows what it is in seconds.

### C5. Keys (checklist 33)

| Key | Type | Default | Where |
|---|---|---|---|
| `marathon_archive_after_days` | int 0–365 | 7 | Marathons registry, mock row, label |
| `golive_expiry_keeps_marathon_channels` | bool | on | Go-live registry, mock row, label |
| `marathon_archived_word` | text | *Archived {when} — runs, people and posts are kept.* | the sentence posted/edited where a marathon's message is |
| `marathon_archive_title` | text | *Archive* | the site foldout title (site words are usually constants; this one is posted nowhere — keep it a constant, listed here only so the decision is visible) |

Every other new sentence the bot posts (the Archive it confirm, the Restore answer, the Remove words) is a key too. Registry count moves from 497 accordingly; `docs/info/architecture.md` gets the schema and key lines.

## D. Tests, docs, gate (the standing rules)

Tests mirror the package: `tests/storage/test_db.py` (schema 70 on a fresh file and on a downgraded 69; the archive twins' column lists equal the live ones), `tests/test_marathon_channels.py` (`carries_marathons`), `tests/cogs/content/test_spotlight.py` (an expired row that carries a feed is kept with the new log row; one that carries nothing is deleted as before; the key off restores deletion), `tests/cogs/content/test_marathon.py` (the tick archives one ended marathon per pass after the grace; runs and people travel; windows/spotlights are dropped; the feed dedupe sees the archived ref; Restore copies back paused), `tests/api/tools/test_marathons.py` (the archive route, the archived id, Restore), node tests for any moved word. Docs the build writes: this file's **Deviations** and **What was NOT verified** at the foot, `code-notes.md`, `architecture.md`, `sweeps.md` rows `MA-a…` (a: a marathon past its end + grace is in Archive with its runs; b: Restore brings it back paused; c: an expired SS4C-style row is kept, its feed alive; d: a feed does not re-add an archived event). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md` / the READMEs. Gate: `ruff check .`, `ruff format --check` on touched files (pre-existing failures reported), `python -m pytest -q -n auto`, `node --check`, `node --test site/mock/*.test.mjs`, `node site/mock/check.mjs` against a mock started from the branch, a headless render of the Archive foldout and an archived drawer — LOOK. Commit at clean boundaries in this order: schema + twins test → the expiry rule → the tick + Remove/Archive/Restore → the site → docs.

## E. Dispatch notes for the next conductor

- ⚠️ **Cloud agents:** on 2026-09-26 the Agent tool's `isolation: "remote"` silently ran three agents LOCALLY in `.claude/worktrees` (feedback drafted; `TODO.md` has the account). Check where an agent is actually running before assuming it bills credits. If a genuinely remote run is wanted, start it from Claude Code on the web.
- Build **`marathon-archive` first**, then **`marathon-inbox`** (`marathon-inbox-design.md`) on top of it — the inbox reads the archive (C3) and both touch `cogs/content/marathon.py`, `marathon_feeds.py` and `marathons-section.js`.
- **Deploy order:** the merged `marathon-spotlight` (schema 69) is not live yet. Either deploy it as v174 first (pre-deploy snapshot; then make rows 6 and 7 kept by hand if the owner says yes) or let the archive build ride with it — but schema 69 and 70 must both apply on one boot in order (`ADDED_COLUMNS` and `CREATE TABLE IF NOT EXISTS` are idempotent; verify with a downgraded-68 test).
- Per-feature shadow: `marathon_mode = shadow` still routes posts to the shadow home; archiving posts nothing, so shadow does not hold it.

## Deviations

Written by the build (Opus 5.5, branch `marathon-archive-local`, 2026-09-26). Where the spec and the code disagreed,
the code's pattern won for shape and the spec for behaviour.

1. **The twins are made at boot, not spelled out in `SCHEMA`.** `db.py:ARCHIVED_TABLES` names them and
   `_mirror_archived_tables` builds each from its live table's `PRAGMA table_info` (and adds any column the live table
   has and the twin lacks, every boot). So the §C1 guard *"a future `ADDED_COLUMNS` entry fails a test until its twin
   exists"* became stronger: the twin is grown for you, and `tests/storage/test_db.py` asserts both the equal column
   lists and that a grown live table grows its twin. Mirrored columns keep type, DEFAULT and the `id` PRIMARY KEY, and
   drop NOT NULL / UNIQUE / CHECK (an archive holds what the live row held). Three indexes, not one: the design's
   `marathons_archive_by_guild` plus one on `marathon_id` for each of the runs and people twins.
2. **§B: the open session is not ENDED — the live post is unpinned and the session kept**, as
   `marathon_spotlight.lift` does. Ending it (`_end`, EXPIRED words) would make the very next poll announce the
   still-live stream again, unpinned — a second post in `#go-live` for the same stream. And `_expire` runs holding the
   row lock, so `settle_open_session` (which takes that lock) could not be reused without a deadlock; `_keep` unpins
   by hand. `starts_at` is cleared too, as §B said.
3. **§B applies to `expire_for_event` as well** (a cancelled event), because the rule lives in `_expire`, as
   specified. `golive.spotlight_kept` carries `held_by` (the list of signals), `because: marathon_channel` and
   `expired_because` (the sweep's EXPIRED or `event_cancelled`). The "live marathons row" signal counts a paused
   marathon too — it is still on the list.
4. **The sweep calls off no event; Archive it and Remove do.** A marathon archived by the tick ended a week ago, so its
   events are past; calling them off would post cancellations nobody needs. Remove keeps its old behaviour (calls off
   the linked event and every run event); **Archive it** does the same, so an early archive never strands an approved
   event on the calendar. Ping windows, `marathon_spotlights` rows and a channel spotlight this marathon holds go at
   every archive (the held spotlight is lifted with `because: marathon_archived`).
5. **Remove still logs `marathon.removed`** (one write, one row — checklist 34), with `archived_why: removed` and the
   counts; `marathon.archived` is the sweep's and Archive it's row.
6. **The feed dedupe leaves REMOVED archive rows to the ignore list.** `marathons_by_ref` reads live + archive in one
   UNION but skips `archived_why = 'removed'`: those refs are already on the feed's `ignored` list, and **Forget
   ignored** is the staff override that must still let the feed add them again (the existing behaviour, and
   `tests/cogs/content/test_marathon_feeds.py::test_a_removed_feed_marathon_is_ignored_and_forget_ignored_adds_it_again`).
   A known ref that is archived is never *adopted* by a feed.
7. **The next-event suggestion.** There was no separate "newest ended marathon of a source" read to redirect: the
   suggestion is written on the live marathon the day after it ends and travels into the archive with the row (a week
   later). What now reads the archive is `marathon_by_ref`, the "already on the list" check, so an event followed
   once and archived is linked, never added twice. A staff notice's Add it / Not this one pressed after the move
   answers *no such marathon*, in words.
8. **The inbox thread (§C3) does not exist yet** — `marathon-inbox` is the next build. `marathon_archived_word` is
   registered and used where an archived marathon's message is today: the archived drawer's header and the API's
   `archived_word`. Nothing is edited on Discord at the move except the board's pin (unpinned if it still carries one).
9. **Eleven keys, not four.** `golive_expiry_keeps_marathon_channels` (Go-live), `marathon_archive_after_days`,
   `marathon_archived_word`, and — per *every other new sentence the bot posts is a key* — `marathon_archive_question`,
   `marathon_archived_said`, `marathon_remove_question` and `marathon_removed_said` (these two replace the code
   constants `marathon.REMOVE_QUESTION` / `REMOVED`, now deleted), `marathon_restore_question`,
   `marathon_restored_said`, `marathon_restore_taken`, `marathon_not_archived`. `marathon_archive_title` stayed a
   site constant, as §C5 said. The site's own confirm bodies (Archive it, Remove, Restore) are site constants like the
   existing `REMOVE_BODY`; the answers they show come from the keys.
10. **Restore refuses in words when a live marathon has the same schedule link** (409, `marathon_restore_taken`) — the
    live table's `UNIQUE (guild_id, schedule_url)` would otherwise raise. It also clears `board_pinned`.
11. **Tests mirror the new modules**: `tests/test_marathon_archive.py` and `tests/cogs/content/test_marathon_archive.py`
    carry the tick, the move, Restore and the dedupe (the design listed `test_marathon.py`; the repo rule is one test
    file per source file).
12. **The `/event` panel.** *Archive it* sits on the card's row 4 (row 3 already holds up to five buttons); the root
    gains **Archive…** (row 3): the 25 newest archived, a pick, a Restore confirm, then the restored card — Restore
    from Discord too, so the decision is reachable both ways (checklist 33).
13. **The tick archives in every `marathon_mode`, `off` included** — archiving posts nothing — one marathon per guild
    per tick, the one that ended longest ago.
14. **The archived People card** reads its own archived pairings plus the live every-schedule ones and fills no Go-live
    row, spotlight or near-miss — it has no moves.
15. **The mock** keeps an archived marathon's runs and pairings in the same arrays keyed by `marathon_id` (only the row
    moves to `state.marathonArchive`); it has no tick.

## What was NOT verified

- **Nothing met Discord.** The bot was not run; no panel button was pressed in a real client (the Discord side —
  *Archive it*, *Archive…*, the Restore confirm — is exercised through `build_card` / `build_panel` / `build_archive`
  in tests only). The board unpin at archive was not exercised against Discord.
- **The live database was not read and the migration has NOT run on it.** Schema 70 was proved on fresh files and on
  downgraded 69 and 68 files in tests only. Rows 6 (`speedstuff4charity`) and 7 (`retrogaminglivetv`) were not
  touched; this build does nothing about their current dates beyond the §B rule once it is deployed.
- **The event call-offs on Archive it / Remove** are the existing Remove code path; the archive tests stub
  `cancel_linked_event` to prove it is (and is not) called, they did not re-run a real cancellation.
- **Feeds other than GDQ** (Oengus, horaro, horaro events, Fastest Furs, Lady Arcaders) were not run against an
  archived ref; only `marathons_by_ref` itself is tested. Lady Arcaders' prober now sees archived event numbers as
  known — untested.
- **Rendered** in `chrome-headless-shell` 149.0.7827.22 over raw CDP against this branch's mock (`MOCK_PORT=8811`):
  the Archive foldout open at 1400 and 390 px, the archived drawer (SGDQ 2026) at 1400 px with the day folds open, and
  ESA Winter 2026's at 390 px; no page errors, no horizontal scroll at 390. The flow **Archive it → confirm** (the
  drawer closed, *Archive · 3*) and **Restore → confirm** (*…is back on the list, paused*, the drawer offered Resume
  and Archive it, *Archive · 2*) was clicked through in the same browser. NOT rendered: the light theme, **Show N
  more** (the mock seeds two), the Events card's marathon line for an archived marathon.

