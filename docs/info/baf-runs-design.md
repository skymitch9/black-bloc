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
| **F1 — where it lives** ✅ **DECIDED A (owner, 21:4x: "A")** | (A) its own page `runs.html` — *BaF runs* — linked from the Events page's marathons section and the nav; (B) a fourth section on `events.html` | **A.** A sortable table with filters, a per-game view, import/export and a staff editor is a page's worth; Events is already three sections and the owner just moved weekly questions *into* Posts to keep page count down, but this is a different question (history, not what is coming) and nothing on Events owns it. |
| **F2 — how the history gets in** ✅ **DECIDED A (owner, 21:5x: "a")** | (A) an **isolated importer**: *Import a GDQ event…* on the runs page takes a tracker event link, reads its runs through the same `marathon_sources` reader and the same pairing helper, and writes them straight into the runs store with `how = imported` — never creating a marathon row, so no board, thread, event, reminder, ping or shoutout can fire for a past event; (B) staff add the past event as a marathon by its link and let the normal machinery read it, with every announcer taught to skip an ended event | **A.** B touches eleven marathon modules to make "ended before we saw it" safe; A touches none of them. Hotfix specials and BtB before the bot are NOT on the tracker — those come in by CSV or by hand (D6) either way. |
| **F3 — the Discord lookup** ✅ **DECIDED A (owner, 21:5x: "do both the /run look up and the page, let pt have it")** — section 5.8 | (A) build `/runs` now: one command → an ephemeral panel with a game search box, answering *"Shredder's Revenge — seen 2 times: BtB 2026 (runner), SGDQ 2025 (runner); last 2026-06-30"* with a *Open on the site* button; (B) ship the page first, add the lookup only if PT still wants it after a month with the page; (C) never | **B.** The owner's *"we CAN but we shouldn't"* and the panels rule both point at the site; PT's wish was *"just the info"*, which the per-game view answers in one search. If built later it is a panel, not a text reply, and its answer template is a settings key. |

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

### 5.7 Settings keys (all under the Marathons group; keys 1242 → 1247)

| Key | Type | Default | Decides |
|---|---|---|---|
| `runs_sources` | list | `gdq, gdq_hotfix` | which marathon sources count (D1) |
| `runs_parts` | list | `runner` | which `part` values make a run a BaF run (D2) |
| `runs_lookup_title` | text | `{game}` | the heading of one game's answer in the `/runs` panel (5.8) |
| `runs_lookup_line` | text | `{date} · {event} · {category} · {runners}` | one run's line under a game |
| `runs_lookup_none` | text | `Nothing in the BaF runs database matches **{query}**.` | the panel's answer when no game matches |

The three word keys exist because the panel posts them (every word the bot posts is editable on the site). The page's own labels are site strings, not bot posts.

### 5.8 The `/runs` lookup panel (F3-A)

One command, one panel, staff-visible like the marathon controls (`command_visibility`): `/runs` opens an ephemeral panel whose first move is **Search…**, a modal with one box (*game*). The answer is one ephemeral embed built from the SAME `baf_runs.py` query the page uses (5.5), never a second implementation:

- games whose key contains the typed text (case-insensitive), at most 5, each a field: title = `runs_lookup_title`, body = *seen {n} times, last {date} at {event}*, then one `runs_lookup_line` per run newest first, at most 5 lines per game and *… and {more} more* after;
- no match → `runs_lookup_none`;
- buttons: **Search again** (the modal), **Open on the site** (link to `runs.html` with the query in the hash, so the page opens on that filter).

Nothing is posted publicly; the panel is ephemeral and writes nothing. One log row `runs.lookup` with the actor and the query.

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
- No public Discord post from the lookup: the `/runs` panel is ephemeral (5.8).

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

One Opus build, ~300k (core + db + api + web + cog), branch `baf-runs`: schema 97, `baf_runs.py`, the API module, `runs.html` + `runs.js`, the `/runs` panel as a cog under `cogs/content/`, tests mirroring each. Then the importer against a real past event on the local mock, then merge-test-deploy with the pre-deploy snapshot, per the standing order. The request card moves to *ready to check* with `how_to_test` = the page link, so PT checks it himself.

## Deviations

Filled by the build (branch `baf-runs`, 2026-10-19). Numbered; each says why.

1. **`baf_runs` has one more column, `run_ref`** (the tracker run's id), with a partial unique index on `(guild_id, event_source, event_ref, run_ref)`. §5.5 had no per-run reference on an imported row, and "a second import of the same event adds 0" needs one; the index makes it hold under two clicks too (checklist 6).
2. **Clear edits is `PUT /api/runs/{key}` with `{"clear": true}`**, not its own route; §5.6's route list is otherwise as written.
3. **`GET /api/runs` answers an object** `{rows, events, series_names, sources, parts}` rather than a bare list: the editor's Event select needs every GDQ-source marathon incl. archived, and the Series box needs the existing series as suggestions, in the same read.
4. **The importer's *Pair…* is a member picker whose answer applies to that import only** (`pairs` in the request), not the marathon pairing modal. The existing pairing route (`pair_runner`) needs a marathon, rematches it and re-syncs its board, and writes `marathon_people` — the brief's hard rule is that this feature never writes the marathon feature's tables and never calls anything that posts. A pairing made on the Events page (*everywhere*) IS read by the importer.
5. **`runs_sources` and `runs_parts` are type `enums`** (the registry has no plain `list` type), with choices = every marathon source / every part. Same defaults as §5.7.
6. **A tracked run's Remove is an override row with `field = 'excluded'`** in `baf_run_edits` (the PK is per field, so exclusion is its own field). Restore deletes it.
7. **Rows the importers write are `how = imported`** (CSV and GDQ alike), and Remove on any `baf_runs` row — hand or imported — deletes it after an *Are you sure*; only a tracked run has Restore.
8. **The GDQ importer leaves out a run that has not started** (counted as *not run yet* in the dry-run line), per D3 — only completed runs count.
9. **A CSV `series` cell only fills a game that has no series yet**; it never overwrites a tag staff set.
10. **A hand or imported row whose event matches a live marathon** (same source and ref) links to `schedule.html#marathon-<id>` too, not only tracked rows.
11. **Phone width (390 px): the shared `table()` restacks each row into a labelled card** instead of scrolling sideways — that is the site-wide table's own phone layout, and the page does not scroll sideways (measured in headless Chrome at 390 px: `scrollWidth` 390 = viewport, table 324/324).
12. **The `/runs` panel's timeout (10 min) and button labels are code constants**; the words that build the answer are the `runs_lookup_*` keys. The *seen N time(s), last … at …* line was a constant too until 2026-10-19 (branch `post-to-test-more`): it is now the key `runs_lookup_seen` (text, Marathons, `{n}` `{date}` `{event}`), so §5.7's five keys are six.
13. **Finding, not a change — §2/§4's assumptions measured 2026-10-19:** the GDQ tracker DOES serve an ended event's runs (BtB 2025, event 54: 46 runs read; SGDQ 2025 by short link `sgdq2025`: 155 runs). And **Back to Black is on the tracker** (`BTB2025` = event 54, February 2025), so BtB history from 2025 on comes in by *Import a GDQ event…*, not only by CSV as §4 F2 assumed. Hotfix specials were not checked.

## Genre and the filter row — 2026-10-20

Owner, 2026-10-20 06:4x–07:0x Phoenix: *"We didn't fill in series, I want to add a genre column too"*, *"Event and runner need to be drop downs before they become overwhelming"*, *"The how category seems useless"*, *"We need a filter by series and genre"*. Branch `runs-genre`.

**Genre, the same shape as series.** Schema 98 -> 99: `baf_series` gains `genre TEXT NOT NULL DEFAULT ''` (table name kept; a row holds series, genre or both, and is deleted when both are blank). Rows and games carry `genre`; `GET /api/runs` adds `genre_names` and a `genre` query filter; `PUT /api/runs/genre/{game_key}` beside the series route (staff write, same refusals); `set_genre` beside `set_series` over one `set_tag`; log kind `runs.genre_set`. CSV: a `genre` column after `series` on export; on import it fills only a game with no genre yet. Search matches genre. Page: a sortable Genre column on the Runs sheet, a Genre box with its own suggestions beside Series on the Games view, a Genre field in the row editor.

**The `/runs` panel.** Series was never shown there before this. New word key `runs_lookup_tags` (default `{tags}`): a line under each game's heading, drawn only when the game has a series or a genre. `{series}`, `{genre}` and `{tags}` (the set ones joined by ` · `) also work in `runs_lookup_title` and `runs_lookup_seen`; every older placeholder still works. The *seen N time(s), last … at …* line is the `runs_lookup_seen` key (verified; no code constant carries the words).

**The filter row.** The How chip row is gone (the sheet's How column stays — it carries the edit pencil and the *removed* / *edited* state). Event, Runner, Series and Genre are native selects beside the search box, built by ONE helper `filterSelect` in `ui.js` from `countedChoices` in `listfilter.js`: an *All events* / *All runners* / *All series* / *All genres* first option, each choice with its row count, *No series* / *No genre* with theirs; events newest first by their latest run, the rest by name. Year stays chips. Series and Genre are also drawn on the Games view and filter it (counted by games there). Every filter is in the hash.

### Deviations (continued)

14. **The filters are in the hash for the first time.** The brief said to write the hash "exactly as chips did"; the chips never wrote it (only `q` and `view` were). Now `year`, `event`, `runner`, `series`, `genre` and `removed` ride the hash beside `q` / `view`, and `readHash` is authoritative (a `#q=` link from the Games view clears the rest).
15. **A *Removed (N)* chip replaces the How row's *Removed* chip.** The How row was the only way to see a removed run, and so the only way to reach Restore; dropping it whole would have stranded every Remove (staff final say). The chip shows only while there is a removed run or it is on. Checklist item 44.
16. **`runs_lookup_tags` is a new key** (keys +1), not only placeholders on the existing ones, because *"genre shows only when set"* cannot be done by a template that is always drawn.
17. **Selects with nothing to choose are not drawn** (the chip rows hid at ≤2 choices); a set value keeps its select drawn, and a value that is no longer a choice shows as `value (0)`.
18. **No skeleton line was added to `docs/deploys.log`.** `scripts/deploy.ps1` reads the LAST line's column 3 as the live commit (and refuses if it is not a commit) and numbers the release from its `vNNN:`; a pre-written skeleton with blank fields would refuse or mis-number the next deploy (the v221 `4a7c1f3a` incident in `docs/access/deploy.md`). The script appends its own skeleton after the deploy; the conductor fills it.

## Genre families — 2026-10-20

Owner, 2026-10-20 07:1x–07:2x Phoenix: *"We need very tight genres"*, *"Action isn't really a solo genre so I think we don't index by it, we'd index by adventure and rogue like probably but don't remove the word action"*, *"Kart racer and a normal racer should index together if someone searches racer"*. Branch `genre-families`.

**What is shown and what is indexed.** The genre a staffer types stays as typed: the Genre column, the Games-view box, the editor, the datalists, the CSV and the `/runs` tags line all show it (*Action roguelike* keeps *Action*). What the page and the API INDEX by is the game's **genre family**, carried as `genre_family` beside `genre` on every row and every game.

**The rule** — one function, `black_bloc/runs_genres.py:genre_family(text, qualifiers, families)` (exposed as `baf_runs.genre_family`), and its twin `listfilter.js:genreFamily`, both held to `tests/fixtures/runs/genre_families.json`:

1. Normalise: lower case; anything not a letter or digit (hyphens, slashes, apostrophes) is a space; spaces collapse.
2. Try the FULL normalised text against each family's name and aliases, in file order.
3. Then the text with the qualifiers taken out (whole words, the longest qualifier first), against the same list.
4. First match wins. No match: the stripped text is its own family, so nothing disappears (*Puzzle* is the family `puzzle`). If stripping leaves nothing (*Action* alone) the full text is the family.
5. A family name displays Capitalised (*Racing*).

| Key (Marathons) | Default | Decides |
|---|---|---|
| `runs_genre_qualifiers` | `action, 2d, 3d, kart, third-person, first-person` | words left out before step 3; may be blank |
| `runs_genre_families` | six lines: `racing`, `platformer`, `roguelike`, `shooter`, `adventure`, `fighting`, each `family: alias, alias, …` | the families; a malformed line is skipped on read, and the Settings page refuses it at save naming the line (*Line 7 of the genre families, `…`, is not a family…*) |

Both are read on every request, so an edit lands on the next read.

**Where the family is used.** The Genre drop-down on the Runs sheet and the Games view lists families with counts (*Racing (2)*), filters by family, and writes `genre=<family>` to the hash (`__none` still means no genre; an older `#genre=Metroidvania` link is lowercased onto its family). The search box matches the typed text, the family name and every alias of that family, so *racer* finds a *Kart racer* and a *Racing* row. `GET /api/runs?genre=` takes any text and filters by its family; the payload adds `genre_families` (`[{family, aliases}]`). The `/runs` panel's Search matches a game's name or its genre, family and aliases.

**Also folded in (the v240 owed item):** the `/runs` panel's last three code constants are word keys — `runs_lookup_count` (`{runs} run(s) · {games} game(s)`, `{runs}` `{games}`), `runs_lookup_more` (`… and {more} more`, `{more}`), `runs_lookup_no_date` (`no date`). Keys +5 (1242 → 1247).

### Deviations (continued)

19. **The rule lives in a new leaf module `black_bloc/runs_genres.py`, not in `baf_runs.py`.** The Settings validation must parse `runs_genre_families` with the same parser, `settings_store` cannot import `baf_runs` (which imports `settings_store`), and the repo's pattern for a validator's parser is a leaf module (`points.xp`). `baf_runs` imports `genre_family` and the parsers and is where every caller reaches them.
20. **The JS twin is `genreFamily`, not `genre_family`** — the site's exported names are camelCase throughout `listfilter.js`. Same arguments, same fixture.
21. **A genre that is ONLY qualifiers (*Action*) is its own family `action`** rather than blank, so a typed genre never reads as *No genre*.
22. **The Games view's own table search (the shared `table()` box) is unchanged** and does not reach aliases; the Genre drop-down there filters by family. The search that reaches aliases is the Runs sheet's.
23. **The mock seeds two more hand rows** (*Mario Kart 8 Deluxe* — *Kart racer*, *F-Zero GX* — *Racing*) so the family has something to show locally.

## Loose search — 2026-10-20

Owner, 2026-10-20 08:1x Phoenix: *"so /runs is gonna be an issue because if you dont know the exact name it doesnt work"*. Branch `runs-loose-search`.

**The defect.** `lookup` kept a game only when the typed text was a SUBSTRING of its key or genre text, and the page and `?q=` were the same substring test over `text_of`. *DKC2*, *donkey 2*, *kong country donkey*, *sekiro shadow die*, *Sonic* (a series), a runner, a category or an event word all answered *nothing matches* in `/runs`.

**The rule** — one function each side on one fixture, the `genre_family` pattern: `black_bloc/runs_search.py:matches(query, haystack)` and `site/public/assets/listfilter.js:runsMatches(query, haystack)`, both held to `tests/fixtures/runs/search.json` (`tests/test_runs_search.py`, `site/mock/listfilter.test.mjs`).

1. Normalise both sides the way `runs_genres.normal` does (lower case, anything not a letter or digit is a space, spaces collapse, digits kept).
2. Every query word must hit the haystack, in any order.
3. A word hits a haystack word when it is (a) a prefix of it; (b) within ONE edit of it (insert, delete, replace, adjacent swap) and the query word has 5+ letters; or (c) letters then optional digits where the letters are the initials of a run of consecutive haystack words on ONE line and the digits are the word right after that run (*dkc2* = *Donkey Kong Country 2*, *jfg*, *sdt*; *dkc3* is not DKC2). Initials need 2+ letters.
4. A digits-only word matches a whole number only (*2* finds *Country 2*, never *2025* or *2D*).
5. An empty query matches nothing; the page and `?q=` skip the filter on a blank query, so they still show everything.

**The haystack** is built in ONE place, `baf_runs.text_of(row, rule)`: one field per line — game, series, genre, the genre family and every alias, category, each runner's display and source name, event, note. `view` ships it on every row as `search`; `filtered(q=)` (the API) and the page (`row.search`, `match: 'words'`) search it, and `lookup` matches a game by the union of its runs' haystacks (`text_of_game`).

**The `/runs` panel.** When nothing matches, the answer offers up to three nearest game names (`difflib.get_close_matches` over the game names, cutoff 0.5) through the new `{suggestions}` placeholder of `runs_lookup_none` (default `Nothing in the BaF runs database matches **{query}**.\n{suggestions}`; the names joined by ` · `; blank renders nothing extra). The `runs.lookup` row gains `suggested: N`. Search again opens the form with the query already typed. No new key (still 1247).

**Other pages.** `listfilter.matches` / `passes` take `match: 'words'`; only `page-runs.js` passes it. Every other page's search is the unchanged substring test.

### Deviations (continued)

24. **`lookup` returns `Found(games, suggestions)`** (a NamedTuple) instead of a bare list, so the suggestions travel with the answer; the panel is its only caller.
25. **Note kept in the haystack.** The brief's list left the note out and the first draft dropped it from the page; the conductor reversed that (2026-10-20): the note is the haystack's last line, so the page, `?q=` and `/runs` all reach it (the Python side had never searched it before this).
26. **`?q=rogue-lite` now finds an *Action roguelike* game** (`tests/test_baf_runs.py` asserted none): hyphen and space are the same now, and *rogue-lite* is an alias of the roguelike family.
27. **`{suggestions}` carries names only, no words of its own.** A lead-in like *Did you mean* would be a code constant; the default puts the names on their own line under the sentence instead, and staff can word it (`No {query}. Closest: {suggestions}`).
28. **The mock seeds two more hand rows** (*Donkey Kong Country 2: Diddy's Kong Quest* by KnightFan, genre *2D platformer*; *Sekiro: Shadows Die Twice* by Rivet) so *dkc2*, *donkey 2* and a typo have something to find locally; the mock mirrors `text_of` as `runsSearchText`.
29. **The Games view's own table box is unchanged** (still the shared substring search, like Deviation 22); the loose search is the Runs sheet's and `/runs`.

## Folding renamed tracked runs — 2026-10-20

Owner, 2026-10-20 08:5x Phoenix: *"fix the duplicate"*. Branch `runs-renamed-collapse`.

**The defect.** Game Masters (marathon 12, a Hotfix show, 2026-10-10 02:00–04:22Z) showed *Donkey Kong Country 2* twice on the sheet and *times featured 2* on the Games view. It was one run by Ryan Ford. The Hotfix sheet renamed the row's category during the show (a misread time cell `12:28:48 AM`, then *True Ending*, then *102%*). A Hotfix run's `external_id` is `game/category` (`marathon_hotfix._runs`), so each rename became its own `marathon_runs` row: 171 (dropped), 172 (done), 173 (done). The view counts every `done`/`live` tracked row, so it counted 172 and 173 both. The conductor removed t172 by hand at 09:1x (a `baf_run_edits` exclusion, restorable).

**The rule.** One place, `baf_runs.fold` (called by `view` after the tracked rows are shaped and the edits overlaid, before the hand rows are added). Tracked rows of ONE marathon with the same `game_key` and the same runner set (each counted person's `user_id`, else the lowercased name) are ONE run when their windows overlap, or their starts are at most `runs_same_run_minutes` apart. A window runs from the shown date to `actual_ended_at`, else `ends_at`; with no end, or an end before the start, it is the start alone. Groups chain: A near B and B near C is one run.

| Key (Marathons) | Type | Default | Decides |
|---|---|---|---|
| `runs_same_run_minutes` | int, 0–1440 | `90` | how far apart two starts may be and still be one run; **0 folds nothing** (every tracked row shows, as before this build) |

Keys 1247 → 1248.

**Inside a group:**

1. **The newest run id wins.** Its key, date, event, category, runners and state are the row. The older rows are gone from the sheet, the Games counts, `filtered` (`?q=` and every filter), `export_csv`, `lookup` and so the `/runs` panel. All of those read `view`, so the one fold serves them all (tests: `test_games_export_and_lookup_count_a_renamed_run_once`, `test_a_renamed_tracked_run_is_one_row_carrying_its_folded_keys`).
2. **The surviving row carries `folded`**: the keys it absorbed, newest first. Every row has `folded` (empty when nothing folded) and `carried` (below).
3. **A row staff removed stays removed.** An older row with an exclusion is NOT folded. It stays its own removed row under *Removed (N)*, where Restore reaches it; restored, it folds. The live t172 is this case, so on the live page DKC2 shows once with no pill.
4. **Removing the surviving row removes the run.** When the newest row is removed, every older row of the group folds into it, so the whole group shows as ONE removed row and Restore brings the run back. Without this, Remove on the survivor would bring the next-newest rename back as the run.
5. **Staff edits.** The survivor's own edits apply as they always did. A staff edit on an OLDER row's *category*, *runners* or *note* is carried onto the survivor only if the survivor has no stored edit of its own for that field. The newest older edit wins. The survivor lists the fields in `carried`, and `tracked` holds the survivor's source value, so the editor still shows *tracked value: …*. Carried fields are not in `edited`, so *Clear edits* clears only the survivor's own edits. An older row's *date*, *event* or *game* edit is not carried: those decide the grouping itself.
6. **Staff can override a carried value back to the sheet's.** Saving the source value on a field that is `carried` stores it as an edit, even though it equals the source. That edit blocks the carry, so staff keep the final say.

**The page.** In the How cell, a folded row gets a small pill, *2 rows*, whose tooltip lists the keys. The row editor shows *Folded rows: t172* under the Date. Nothing else changes, and nothing explains it.

**Hidden rows cannot be edited.** `find("t172")` answers nothing while t172 is folded, so an edit, removal or restore by its key refuses *not in the database any more*. The rows to act on are the visible ones. Set `runs_same_run_minutes` to 0 to reach every tracked row one by one.

### The tracker: should it pair a renamed sheet row with the existing run? (recommendation, not built)

**It already tries to, and here that pairing failed.** The tracker does not need new pairing logic. The 2026-10-04 `run-identity` build ([`marathon-hotfix-design.md`](marathon-hotfix-design.md) *a renamed run keeps its identity*) made `marathon.diff` pair a lost row with a fresh run in the same slot (`marathon.renames` / `same_slot` / `rekeys`, logged as `marathon.run_renamed`). That keeps the row id and with it the held counts, `reminders_sent`, shout and thread ids, `live_at` and damping state. For DKC2 it did not fire, so the first step is a diagnosis, not a build. Read the `marathon.run_renamed` and `marathon.schedule_changed` rows for marathon 12 on 2026-10-10, and the stored `sheet_at`, `order_no` and `people` of runs 171–173 (read-only, through the operator token). The likely misses can each be named in the code:

- (a) The planned start moved by more than `marathon_move_minutes` (5) AND the order changed. A Hotfix start is a running cursor over the earlier rows' estimates, so a misread time cell shifts every later start. `same_slot` then needs the same `order_no` within 12 h.
- (b) More than one lost row carried Ryan Ford's runner set in one read. Then `_candidates` also demands `same_words` at 0.93 or more, and *Donkey Kong Country 2 / 102%* against */ True Ending* is **0.759**. The run-identity design names exactly this pair as one it refuses.
- (c) The misread row's runner column was shifted too, so the runner sets differed.

If (a) or (b), a narrow change is possible. One idea: a lost row whose game is equal and whose runners are equal pairs on order alone, even when a second lost row shares the runner. But that rule lives in the one reconcile path that moves persisted ids (`rekey_runs`). The pair's held move counts and `marathon.member_run_moved` damping, its posted reminders, the runner's thread links and the board all follow the row id, and a wrong pair would merge two real runs, rewording one runner's live highlight onto another game. That is why the existing rule pairs nothing when it is ambiguous. My recommendation: diagnose first. Change `same_slot` / `_candidates` only if the diagnosis names (a) or (b), and only with a fixture of this show's three reads. Keep this view fold either way: it also repairs history that is already split, which a tracker change would not touch.

The 2026-10-19 FOUND item (*run ids drift on RGLtv's A Fistful of Brawlers*, marathon 14) is a **horaro** marathon. Its `external_id` is the source's id, not a `game/category` slug, so it is the same symptom from a different cause. The fold here does not reach it either way: horaro is not in `runs_sources`.

### Deviations (continued)

30. **A removed survivor takes its whole group with it**, and a removed OLDER row is kept out of the group (rules 3–4). The brief said only that a removed row "still counts as removed"; these two rules are how that holds without Remove on the survivor bringing a rename back.
31. **`carried` is a second payload field beside `folded`.** The brief named only `folded`. `carried` exists so that saving the sheet's value over a carried one is stored (rule 6) rather than refused as *nothing changed*. Without it, staff could not undo a carry.
32. **The mock seeds Game Masters as an ARCHIVED marathon** (id 12, runs 171–173, Ryan Ford paired to the mock member Dax), so the seed does not add a live marathon to the Events page. The mock folds with its own `runsFold` (a mock, not a second implementation the site runs).
33. **No `docs/deploys.log` line, no TODO/DONE edit** (brief).

## Developer, two genres, one genre format — 2026-10-20

Owner, 2026-10-20 09:2x–09:4x Phoenix: *"Do developer, 2 genres maxed, though action-adventure and Action Roguelike need to be a uniformed casing and formatting. Skip universe"*. The ask behind it: Sekiro and a later Dark Souls run should meet though they are not one series (both FromSoftware), and a game may have more than one genre. Branch `runs-developer`.

**Developer, the same shape as series.** Schema 99 -> 100: `baf_series` gains `developer TEXT NOT NULL DEFAULT ''` (added at boot by `ADDED_COLUMNS`; a row is deleted when series, genre and developer are all blank). Rows and games carry `developer`; `GET /api/runs` adds `developer_names` and a `developer` query filter (the text, case and spacing ignored); `PUT /api/runs/developer/{game_key}` beside series and genre; `set_developer` over the one `set_tag`; log kind `runs.developer_set` (`web.runs.developer_set` from the site). CSV: a `developer` column after `genre`; on import it fills only a game with no developer yet. A developer is saved trimmed with spaces collapsed, never re-cased. The page: a sortable Developer column after Genre, a Developer drop-down beside Event / Runner / Series / Genre (`developer=` in the hash), a Developer box with its own suggestions on the Games view, a Developer field in the row editor. The `/runs` panel: `{developer}` joins `{series}` `{genre}` in `runs_lookup_title`, `runs_lookup_seen` and `runs_lookup_tags`, and `{tags}` includes it.

**Aliases reach search.** The one haystack (`baf_runs.text_of`) carries the developer and, when its name or an alias is on a line of `runs_developer_aliases`, that line's name and every alias. So *fromsoft*, *from software* and *FromSoftware* all find Sekiro on the page, in `?q=` and in `/runs`.

**Genre is a short list.** A genre is comma-separated entries. `runs_genre_max` caps how many; a save with more is refused in words (*"**A, B, C** is 3 genres and a game may have 2, so nothing was saved. Keep the 2 that fit best, separated by commas, or raise the most genres a game may have on the Settings page."*, code `too_many_genres`, 400) on every save path (the genre route, Add a run, the row editor), checked before anything is written. A CSV import keeps the first entries up to the cap and its report line says so (*" N game(s) had more than 2 genres, so only their first 2 were kept."*; `genres_cut` in the summary and the `runs.imported` row). Each entry has its own family: rows and games carry `genre_families` (the first is still `genre_family`). The Genre drop-down counts a game once per family of its list (Sekiro *Soulslike, Action adventure* counts once under Soulslike and once under Adventure), `?genre=` and the drop-down match any entry's family, and the haystack carries every family's words.

**One house spelling** — one rule each side on one fixture, the `genre_family` pattern: `black_bloc/runs_genres.py:genre_format(text, qualifiers, families, upper)` and `site/public/assets/listfilter.js:genreFormat(text, qualifiers, families, upper)`, both held to `tests/fixtures/runs/genre_format.json` (`tests/test_runs_genres.py`, `site/mock/listfilter.test.mjs`). For each comma-separated entry: trim and collapse spaces; hyphen and underscore become a space; lower-case it, then capitalise its first letter; the words in `runs_genre_upper` go to capitals wherever they stand; empty entries drop; a later entry of the same family drops (the first stays); entries join with `, `. *Action-adventure* -> *Action adventure*, *Action Roguelike* -> *Action roguelike*, *2d platformer* -> *2D platformer*, *Roguelike, roguelite* -> *Roguelike*. Every save path stores the formatted text, so the stored text is canonical and the column, boxes, datalists, CSV and `/runs` show it as stored.

**The stored genres, once.** `black_bloc/runs_genre_format.py` is a boot data migration (after `one_optout`, before the cogs load, `bot.py:_migrate_runs_genre_format`): every non-blank `baf_series.genre` goes through `genre_format` with its guild's settings; changed rows are rewritten, one `runs.migrated` row per guild names each game's before/after, and the log line is `runs genre format: N game(s) rewritten`. It is idempotent (a formatted genre formats to itself). On the eight live genres the dry run names exactly two: *Action-adventure* -> *Action adventure* and *Third-person shooter* -> *Third person shooter*; *2D platformer*, *Fighting*, *Roguelike*, *Action roguelike*, *Kart racing* and *3D platformer* are untouched (`tests/test_runs_genre_format.py`).

| Key (Marathons) | Type | Default | Decides |
|---|---|---|---|
| `runs_genre_max` | int, 1–5 | `2` | how many genres one game may have |
| `runs_genre_upper` | text, may be blank | `2d, 3d, fps, tps, rpg, jrpg, mmo, rts` | the words a genre writes in capitals |
| `runs_developer_aliases` | text, may be blank | `FromSoftware: fromsoft, from software` / `Nintendo: nintendo ead, nintendo epd` | other names a developer goes by in search; a line with no name is refused at save naming the line |

`runs_genre_families` gains a line `soulslike: souls, soulsborne, dark souls, souls-like, souls like`; the qualifiers default is unchanged. Keys 1248 -> 1251.

### Deviations (continued)

34. **A third key, `runs_genre_upper`.** The brief listed the words that go to capitals as part of the rule and asked for three new Settings keys while naming two; the word list is a decided default, so it is a key (checklist 33) and the fixture carries it beside the qualifiers and families.
35. **`genre_format` takes the rule as arguments** (`qualifiers`, `families`, `upper`), not `genre_format(text)` alone: dropping an entry of the same family needs the families. Without them it drops only an exact repeat; `upper` defaults to the shipped word list.
36. **The developer alias lines use the families parser** (`runs_genres.family_lines`, so names and aliases are matched with case, hyphens and spacing ignored) and the same Settings refusal shape (*Line N of the developer aliases, …*).
37. **The boot migration formats a list but never cuts it to the cap.** Cutting would throw stored words away unasked; a game stored with more genres than the cap shows them all, and its next save must fit. Its log kind is a new `runs.migrated` (routine), not `settings.migrated`, which is about settings rows.
38. **The cap counts entries after formatting**, so *Roguelike, roguelite, Fighting* is two entries and saves.
39. **`?developer=` matches the developer text, not its aliases**; aliases reach search only. Like series, the API has no `__none` for it; the page's *No developer* choice filters on the client.
40. **A refused genre stays typed in the Games-view box** until the page refreshes, as a refused series always did; the stored value is unchanged and the refusal shows under the table.
41. **`filtered(q=)` and `text_of_game` read the row's `search`** (built once in `view` with the alias map) instead of rebuilding the haystack without the aliases.
42. **The mock seeds** Sekiro as *Soulslike, Action adventure* by FromSoftware, DKC2 by Rare and Mario Kart 8 Deluxe by Nintendo, so the two-family counts and the alias search have something to show locally.

## Demo mode and pagination — 2026-10-20

Owner, 2026-10-20 10:5x Phoenix: *"Can we make a fake/test page with like 500 randomly generated entries so PT can attempt to parse through it. Have it paginate by pages of 100 so it's not overwhelming by default. Use random games and categories maybe from speedrun.com."* Branch `runs-demo`.

**Pagination on the real page.** The Runs sheet and the Games view each draw one page of their filtered, sorted rows. Under the table, the one shared `ui.js` `pager` (its client-side form, `pages` given): *Previous* · *page N of M* · *Next*, Previous only past page 1, Next only before the last, nothing drawn when everything fits. The count reads *1–100 of 487* on a paged view and the old *N of M* otherwise. The page rides the hash (`page=3`, written only above 1). Any filter, either search, the sort or the view going back to page 1 is one rule (`runs-state.js` `filterKey` / `settledPage`); a link that carries `page=` keeps it.

| Key (Marathons) | Type | Default | Decides |
|---|---|---|---|
| `runs_page_size` | int, 25–500 | `100` | rows on one page, both views |
| `runs_demo_refused` | text, no placeholders | *This is test data, so nothing is saved. Open the real sheet to change a run.* | what a write in demo mode says; its LAST sentence becomes the link to `/runs.html` |

Keys 1251 → 1253.

**Demo mode.** `runs.html#demo` (the flag leads the hash: `#demo&q=…&page=2`; it survives every filter, the view switch and the Games-view game links). The page loads `GET /api/runs/demo` instead of `/api/runs` + `/api/runs/games` and `runs-state.js` `demoPayload` turns the file into the same two payloads: `genre_families` / `genre_family` with the live Settings genre rule, `search` through `listfilter.js` `runsSearchText` (moved there from the mock, which now imports it; so are `runsGames` and `runsCsv`), the games view through `runsGames`, `series_names` / `genre_names` / `developer_names` from the rows, `events` from the file's event list, `sources` `gdq, gdq_hotfix`, `parts` `runner`. The renderer is the real one. A **Test data** pill sits beside the Runs/Games switch. Every write — Add, Save, Clear edits, Remove/Delete, Restore, the three Games-view boxes, CSV import, GDQ import — goes through one `writeGuard` and is refused before any request in the words of `runs_demo_refused`. Export CSV downloads the demo rows (`baf-runs-demo.csv`, built in the browser). Settings and Logs are the real ones.

**The data.** `black_bloc/runs_demo.json`, made by `scripts/scan/make_runs_demo.py` (gitignored, never committed — only its output is), seed **20261020**. Regenerate from the repo root:

```
.venv/Scripts/python scripts/scan/make_runs_demo.py
```

It caches every speedrun.com answer in `scripts/scan/runs_demo_cache/` (gitignored), so a re-run with the cache gives the same file byte for byte; delete the cache to read speedrun.com afresh (and expect its rate limit, below). Games, categories, series and the genres/developers speedrun.com has are real; runners are INVENTED handles (60, from two word lists; never a name the API returned); events are real event NAMES with real-ish windows (AGDQ early January, SGDQ late June/July, Frost Fatales March, Flame Fatales August, Frame Fatales October, BtB February, the six Hotfix shows one episode a year 2021–2026 as `gdq_hotfix`). **What the file holds (measured 2026-10-20 11:2x):** 500 runs, 120 games, 60 runners, 76 events, 255,073 bytes, dates 2015-01-05 to 2026-09-07; six games at the cap of 12 runs; the busiest handles at 47, 46, 27, 23 and 22 runs; 15 rows (3 %) with a note. speedrun.com WAS reached: 50 API calls over three runs of the generator (32 popular games looked up by name, two bulk pages of 200 recent games for the long tail, 16 series), and its Cloudflare limit refused it three times (error 1015, `Retry-After` 395–605 s; the generator waits it out and paces 4 s a call). ⚠️ **speedrun.com returned NO genre and NO developer for any of the 120 games** (its `genres` / `developers` embeds were empty for every one), so the 32 popular games carry a HAND-WRITTEN genre and developer from the generator's `HAND_TAGS` (real-world facts, listed in the file's `hand_tagged`), and the 88 long-tail games have none — the Genre and Developer drop-downs show *No genre (88)*-style counts. Series are speedrun.com's, for the 32 popular games only (the tail's series were not looked up, to save calls).

### Deviations (continued)

43. **The file is `black_bloc/runs_demo.json`, not `site/public/demo/runs-demo.json`, served by `GET /api/runs/demo`.** `SiteFiles` (`black_bloc/api/assets.py`) serves everything under `site/public/` to anyone; the site's gate is the API (`staff_dependency` on the runs router). A file under `site/public/` would be public. It is package data (`pyproject.toml`) beside `guides_seed.json`; the mock reads the same file.
44. **The Games view's search is no longer the shared `table()` box.** That box hides drawn rows, so on a paged view it would search only the page on screen. It is a state search over the games (still a substring test, Deviation 22), in the hash as `gq=`. Checklist item 47.
45. **The sort is a filter for the page rule** (a sort change goes back to page 1) but is still not in the hash, as before.
46. **The demo file stores the row shape minus what the live rule decides** (`genre_family`, `genre_families`, `search`, plus the always-empty `tracked` / `carried` / `event_ref` / `marathon_id`): they are filled on load, so the file stays small and a Settings edit to the genre families reaches the demo.
47. **Demo events carry index ids** (1…N, `archived: true`) so the row editor's Event select can show them; no demo row links to a schedule.
48. **`ui.js` `notice().say` takes `{href}` and `sentenceFor` passes an error's `tone` / `href`.** That is how the refusal's last sentence becomes the link without a second string; no other page passes either.
49. **Genres and developers of the popular games are hand-written, the long tail has none, and the tail has no series** — see *What the file holds*. speedrun.com had none to give; the brief allowed only what speedrun.com has, and a demo with no genres at all would leave the Genre drop-down nothing to teach.
50. **The popular head is 32 games, not ~80.** Each name lookup is one call and Cloudflare allowed about ten calls per window; 32 popular + 88 long-tail keeps the weighting (the popular games carry 2–6× the weight, five of them 30×) at a cost of 50 calls.
51. **No `docs/deploys.log` line, no TODO/DONE edit** (brief).
