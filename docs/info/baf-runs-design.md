# The BaF runs database — request #13

> Audience: future Claude sessions and the owner. Status: TRACKED · 📐 **DESIGN, not built** (Fable, Mon 2026-10-19 21:4x Phoenix).
> Last verified: **2026-10-19 21:4x** — the request card and its thread read in Discord (`#requests` ▸ thread *#13 Database of BaF runs completed*, nine messages 8:26–9:23 PM); the live data read through the operator token (`/api/marathons`, `/api/marathons/16`, `/api/settings`); the tables read in `black_bloc/storage/db.py`. ⚠️ NOT checked: whether the GDQ tracker still serves the runs of an ended event (section 6 assumes it does, as `marathon_sources.RUNS_URL` reads any event by ref); whether the Hotfix sheet keeps past shows (assumed NOT).

## 1. The ask, verbatim

Request **#13** (PT, Mon 2026-10-19 8:26 PM, accepted by the owner 8:58 PM):

> **Database of BaF runs completed.** This will help us when choosing content to know how frequently and often a game has been featured. Ideally would want to know — what is the game · what is the category · how many times has this game been featured · when is the last time we have seen it live. would want it to archive BaF hotfix specials + BtB specifically. I don't care if its on regular hotfix programming tbh.

The thread, which is the real spec:

| When | Who | Said |
|---|---|---|
| 8:59 | Sky | *"might be the easiest thing you've ever asked for, it exist i just need to expose it into a view. do you want this for any BaF run in any event, any BaF run in a gdq Event, or Only BaF runs in BaF events"* |
| 9:02 | PT | *"**BaF runs in GDQ events.** I had to rethink that because the idea of a run being in BtB immediately followed by Frost is enough that for say Juneteenth we may pass on it"* |
| 9:05 | Sky | *"this is probably a website only view since it'll look ugly in discord … just like a big excel like sheet of each run, which event, date, who ran it? or do you want like groupings by games. better question, how do you want to traverse the data to be able to see patterns"* |
| 9:12 | PT | *"A big sortable excel sheet I can manage, data don't scare me (**probably should add runner** to these data now that I think about it) · whatever is easiest that if I call the bot (let's say I /liveRuns as a command) and give it some inputs, it can read said sheet and churn out the answer for us in Discord … 'we've seen Shredders Revenge on stage 2, times, for events A and B, by runners XYZ'"* |
| 9:15 | Sky | *"we have a website. I could add a **series tag** too, that way you can tell if we've seen 500 zelda games or even worse 500 kaizo games of various mario versions. okay let me cook on the view for a bit, do some mocks, I might send you a few different pages to view as test to dial in what you want"* |
| 9:21 | PT | *"I don't play in bots I play in data and Discord is ghetto … I mean commands like dis for just the info not a full spreadsheet"* (screenshot of `/ask`, `/automod`) |
| 9:23 | Sky | *"i mean we CAN but we shouldn't"* |

So the deliverable is: **(1) a sortable, filterable table of every BaF run in a GDQ event, with the runner; (2) a per-game view answering times-featured and last-seen; (3) a series tag per game; (4) PT can manage the data himself; (5) a Discord lookup is wanted by PT and doubted by the owner — a fork, section 4.**

## 2. What already exists (measured 2026-10-19 21:3x)

The marathon feature already records every run of every tracked marathon:

| Table | What it holds | Relevant columns |
|---|---|---|
| `marathons` / `marathons_archive` | one row per tracked event; archived whole `marathon_archive_after_days` (7) after it ends | `name`, `source` (`gdq`, `gdq_hotfix`, `horaro`, `oengus`, `fastestfurs`, `ladyarcaders`, `horaro_events`), `starts_at`, `ends_at` |
| `marathon_runs` / `marathon_runs_archive` | one row per run, diffed by the source's id | `game`, `category`, `twitch_game`, `twitch_category`, `runners_text`, `people` (JSON: `name`, `login`, `part` runner/host/…, `user_id` when paired to a member), `state` (`upcoming`/`live`/`done`/`dropped`), `actual_started_at`, `actual_ended_at`, `scheduled_at`, `live_because` |
| `marathon_people` | staff pairings runner-name → member, per marathon or *everywhere* | `runner_name`, `user_id` |
| `marathon_baf_overrides` | staff saying a member counts as BaF (or not) regardless of role | `user_id` |

`marathon.ours(people_of(row))` is the one canonical "is this one of ours" rule (member paired + BaF role or override, `counts is not False`). **The runs view reuses it; it does not grow a second rule.**

Live right now: 9 marathons (4 `gdq`, 3 `gdq_hotfix`, 2 `horaro`), 108 runs, **5 ours** (4 in RGLtv's horaro event, 1 in Games Done Hitless). The three Hotfix shows tracked (`marathon_hotfix_shows` = *GDQueer, Hidden Heroes*) hold **0 BaF runs**. ⚠️ **The bot has only tracked since late September 2026** — every BtB, every Hotfix special and every main GDQ before that is NOT in the database. Section 6 is how the history gets in; without it the page answers "once, last week" for everything.

## 3. Decisions taken from the thread (no fork needed)

| # | Decision | Why |
|---|---|---|
| D1 | **Scope = runs in GDQ-source events**: `source IN (gdq, gdq_hotfix)` — main GDQs, GDQ Express, Hotfix shows and specials, BtB. Horaro / Oengus / RGL runs are NOT counted. | PT, 9:02: *"BaF runs in GDQ events"*. Configurable both ways: key `runs_sources` (list, default `gdq, gdq_hotfix`). |
| D2 | **A run is a BaF run when one of its people is ours AND their `part` is `runner`.** Hosting or commentary does not count. | PT counts runs, not appearances. Key `runs_parts` (list, default `runner`), so a staff who wants hosts counted flips it. |
| D3 | **Only `done` and `live` runs count.** `upcoming` and `dropped` never appear. | "runs completed" |
| D4 | **The runner is a column** and the per-game view lists distinct runners. | PT, 9:12 |
| D5 | **A series tag per game**, staff-set on the site, blank until set. | Sky, 9:15 |
| D6 | **PT manages the data himself**: add a run by hand, edit any field of any run, remove, import CSV, export CSV. Hand-added rows carry `added_by`; a tracked row that staff edit keeps the source value beside the edit (section 5.3). | PT, 9:12: *"data don't scare me"* |
| D7 | **No new mode switch.** The view is read-only over data the marathon feature already governs (`marathon_mode`); the writes are staff edits, not bot posts. Nothing posts to Discord. | The switch audit of the same day ([`switch-audit-2026-10-19.md`](switch-audit-2026-10-19.md)) — do not add a 21st three-way. |
| D8 | **Staff can read and edit; members cannot see it.** Same gate as the marathon controls. The operator token reads `GET /api/runs*`. | staff data about scheduling choices |

## 4. The forks (owner answers one at a time)

| Fork | Options | Recommendation |
|---|---|---|
| **F1 — where it lives** | (A) its own page `runs.html` — *BaF runs* — linked from the Events page's marathons section and the nav; (B) a fourth section on `events.html` | **A.** A sortable table with filters, a per-game view, import/export and a staff editor is a page's worth; Events is already three sections and the owner just moved weekly questions *into* Posts to keep page count down, but this is a different question (history, not what is coming) and nothing on Events owns it. |
| **F2 — how the history gets in** | (A) an **isolated importer**: *Import a GDQ event…* on the runs page takes a tracker event link, reads its runs through the same `marathon_sources` reader and the same pairing helper, and writes them straight into the runs store with `how = imported` — never creating a marathon row, so no board, thread, event, reminder, ping or shoutout can fire for a past event; (B) staff add the past event as a marathon by its link and let the normal machinery read it, with every announcer taught to skip an ended event | **A.** B touches eleven marathon modules to make "ended before we saw it" safe; A touches none of them. Hotfix specials and BtB before the bot are NOT on the tracker — those come in by CSV or by hand (D6) either way. |
| **F3 — the Discord lookup** | (A) build `/runs` now: one command → an ephemeral panel with a game search box, answering *"Shredder's Revenge — seen 2 times: BtB 2026 (runner), SGDQ 2025 (runner); last 2026-06-30"* with a *Open on the site* button; (B) ship the page first, add the lookup only if PT still wants it after a month with the page; (C) never | **B.** The owner's *"we CAN but we shouldn't"* and the panels rule both point at the site; PT's wish was *"just the info"*, which the per-game view answers in one search. If built later it is a panel, not a text reply, and its answer template is a settings key. |

## 5. The page — `runs.html` (under F1-A)

No blurbs. Three views, one search module ([`ui.js`](../../site/public/assets/ui.js) — the shared search/filter chips), the table sorted by date descending by default.

### 5.1 Runs (the sheet)

| Column | From |
|---|---|
| Date | `actual_started_at`, else `scheduled_at`; shown in the viewer's zone, sortable |
| Event | the marathon's name + source word (*GDQ Hotfix*, *GDQ*); links to `schedule.html#marathon-<id>` while the marathon row exists, plain text once only the archive has it |
| Game | `game` |
| Series | the series tag (5.2), blank until set |
| Category | `category` |
| Runner(s) | the ours people with `part = runner`: member display name, the source name in parentheses when different |
| How | *tracked* / *imported* / *by hand*; a pencil opens the row editor |

Filter chips: Event · Series · Runner · Year · How. Search matches game, category, runner, event. **Export CSV** (every column plus ids) and **Import CSV…** (5.4) at the top right; **Add a run…** beside them.

### 5.2 Games (the grouping)

One row per game (grouped on `lower(trim(game))`): Game · Series (editable in place, a text box with the existing series as suggestions) · Times featured · Last seen (date + event) · Runners (distinct) · Categories (distinct). Click a game → the Runs view filtered to it. This is the view that answers PT's four questions in one line.

### 5.3 The row editor (Add a run… / pencil)

Fields: Date (day + time, the shared When picker), Event (a select of every GDQ-source marathon incl. archived, plus *Other…* for a typed event name), Game, Category, Runner(s) (member picker, multi; plus a free-text source name), Series (optional, sets the game's tag), Note. Save writes:

- a **hand-added or imported** run → a row in `baf_runs` (5.5);
- an edit to a **tracked** run → an override row in `baf_run_edits` keyed by the run's `(marathon_id, external_id)`; the view reads the override over the source, the source value stays and the editor shows *tracked value: …* under each changed field. A re-read of the schedule never undoes a staff edit (the edit lives in its own table), and **Clear edits** puts the tracked row back.
- **Remove** on a hand-added row deletes it; on a tracked row it writes an `excluded` override (the run stays in `marathon_runs`, which the marathon feature owns). **Restore** reverses it.

Every write is one `web.runs.*` log row (`added`, `edited`, `removed`, `restored`, `imported`, `series_set`) with the actor and the before/after.

### 5.4 Import CSV… / Import a GDQ event… (F2-A)

- **CSV**: the same columns the export writes. Dry-run first: the page shows *N rows would be added, M skipped (already here), K need a runner match* before anything is written; a row whose runner name matches no member imports with the name only and shows in Runs with the runner unlinked, exactly as the marathon page's *unmatched* list does today.
- **GDQ event link**: a tracker event URL (`read_url` already recognises them). The importer reads `/events/<ref>/runs/`, keeps the runs whose people are ours (through `marathon_people` *everywhere* pairings and the member Twitch links `matched_by` uses), and shows the same dry-run count. Nothing creates a marathon row. Runs the importer cannot match are listed with a **Pair…** beside each name (the existing pairing modal), so PT can pair a 2025 runner and import again.

### 5.5 Storage (schema 96 → 97)

```
baf_runs         id, guild_id, how ('hand'|'imported'), event_name, event_source, event_ref,
                 started_at, game, category, runners_text, people (JSON like marathon_runs.people),
                 note, added_by, added_at, edited_by, edited_at
baf_run_edits    guild_id, marathon_id, external_id, field, value, excluded, by, at   (PK marathon_id+external_id+field)
baf_series       guild_id, game_key, series, by, at                                     (PK guild_id+game_key)
```

The **Runs view is one query**: `marathon_runs ∪ marathon_runs_archive` joined to `marathons ∪ marathons_archive` where `source ∈ runs_sources` and the run is ours (D2) and `state ∈ (done, live)`, overlaid with `baf_run_edits`, unioned with `baf_runs`, left-joined to `baf_series`. One function in a new `black_bloc/baf_runs.py` owns it; the API, the page and any later Discord lookup call that one function (one implementation).

### 5.6 API

`GET /api/runs` (filters as query params, the rows as the page shows them) · `GET /api/runs/games` · `GET /api/runs/export.csv` · `POST /api/runs` · `PUT /api/runs/{key}` · `DELETE /api/runs/{key}` · `POST /api/runs/{key}/restore` · `PUT /api/runs/series/{game_key}` · `POST /api/runs/import` (`dry_run` flag; body = CSV or `{event_url}`). Reads are operator-token readable; writes are staff, each refusing in words (what happened, what it needs, how to get it).

### 5.7 Settings keys (all under the Marathons group; keys 1242 → 1244)

| Key | Type | Default | Decides |
|---|---|---|---|
| `runs_sources` | list | `gdq, gdq_hotfix` | which marathon sources count (D1) |
| `runs_parts` | list | `runner` | which `part` values make a run a BaF run (D2) |

No word keys: nothing here is posted by the bot. If F3 is ever built, its answer template and its *nothing found* line become keys then.

## 6. The history — what the page will say on day one

With nothing imported the page shows the 1 BaF run in a GDQ event the bot has seen (Games Done Hitless). The useful page needs:

1. **Main GDQs** (AGDQ/SGDQ/Express, 2025 → now): *Import a GDQ event…* per event, ~2 minutes each, pairing the names it cannot match. ⚠️ Assumed, not measured: that the tracker serves ended events' runs — the reader hits the same `RUNS_URL`; the build verifies against one past event before shipping.
2. **BtB and Hotfix specials before September 2026**: not on the tracker, not on the current sheet. By CSV (PT keeps a sheet already — *"data don't scare me"*) or by hand.
3. **From here on**: every tracked GDQ-source marathon lands in the view by itself as its runs go `done`; archiving a marathon changes nothing (the query reads both tables).

## 7. What is deliberately NOT in this build

- No VOD links, no run times/PBs (the PBs page owns personal bests), no Twitch clip hunting.
- No automatic series detection; the tag is staff-set.
- No Discord post of any kind, no mode switch (D7).
- No per-marathon "counts / does not count" switch: the source filter plus per-run *Remove* covers *"I don't care if its on regular hotfix programming"*.
- The Discord lookup (F3) unless the owner picks A.

## 8. Verification the build owes

- Row counts: `GET /api/runs` on the local mock equals a hand-run SQL of 5.5 over the same database; a run with a host who is ours and a runner who is not does NOT appear; an archived marathon's run DOES.
- An edit to a tracked run survives the next schedule read (re-read the marathon, re-read `/api/runs`).
- Import dry-run writes nothing (`SELECT count(*)` before and after), the real import writes exactly the dry-run's N, and a second import of the same event adds 0.
- One past GDQ event imported for real on the local mock (section 6.1's assumption measured).
- Export → import round-trips with 0 added.
- The page at phone width (390 px): the table scrolls sideways inside its card, the page does not.
- Review-link in the report: `https://blackbloc.heygabi.ai/runs.html` (or `events.html#sect-runs` under F1-B), and the log rows named.
- The review checklist ([`review-checklist.md`](review-checklist.md)) items on persisted keys, atomic status+value, silent failure, duplicate implementations, unattended migrations.

## 9. Build shape

One Opus build, ~250k (core + db + api + web), branch `baf-runs`: schema 97, `baf_runs.py`, the API module, `runs.html` + `runs.js`, tests mirroring each. Then the importer against a real past event on the local mock, then merge-test-deploy with the pre-deploy snapshot, per the standing order. The request card moves to *ready to check* with `how_to_test` = the page link, so PT checks it himself.

## Deviations

(none yet — filled by the build)
