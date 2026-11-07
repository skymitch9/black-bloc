# Brackets beyond fighting games — kinds, plain-list votes, sports feeds, predictions

> **Audience:** Claude sessions (the build agents first) and the owner. **Status:** TRACKED. Design, not yet built.
> **Last verified: 2026-11-06 18:1x Phoenix** — the decisions below are the owner's answers of this evening, verbatim; the
> data-source facts are the measured probes in [`brackets-sports-research-2026-11-06.md`](brackets-sports-research-2026-11-06.md)
> (from the owner's machine and from the Fly machine). The code facts (tables, moves, files) were read from `main` at
> `3e4d2454`. ⚠️ **NOT checked:** nothing here has run; every "builder verifies" line is a question for the build.
> Secret NAMES only (none here).

The fighting-game engine, storage, Discord side and page are in [`brackets-design.md`](brackets-design.md). This doc
adds to it; nothing there changes for a fighters bracket.

## The ask and the decisions (verbatim, 2026-11-06)

- The ask: *"Our bracket is cool but fighting game focused. Can we add to it, I want a way to make and compare sports
  brackets too for final 4 basket ball, playoffs etc. Maybe a way to dynamically get the scores for the brackets and
  auto complete team names for sports and schools. Maybe players too. Do research, this will exist in bracket but another
  option for sports or fighters. Also make this a template so we can do other brackets like best candy bar."*
- **Q1 leagues** → *"D this feature has no rush so no need to rush a part of it out"*: every league in one build — NCAA
  men's and women's basketball, NFL, NBA, NHL, MLB. No early slice.
- **Q2 predictions** → *"A"*: every member fills a full pick sheet before the first game; one lock at tip-off; points by
  round 1-2-4-8-16-32; a leaderboard on the page and in the thread; staff may edit a sheet.
- **Q3 plain-list brackets** → *"C"*: the organiser chooses per bracket at creation — member votes (two buttons on the
  card, a timed round, the winner advances when it closes, staff override) or decided by hand.
- **Q4 when a free feed dies** → *"A"*: free only; every source has a fallback; when both fail the bracket says so and
  staff enter results by hand. No paid key.
- *"Also make sure we can manually add or edit items in case of breakage"* → every feed-written thing has a staff /
  organiser edit (entrants, seeds, scores, winners, game times, the structure itself), and a sports bracket can be built
  entirely by hand with no feed.

## The one idea: a KIND on every bracket

`tournaments.kind` — `fighters` (as built) | `sports` | `list`. Chosen FIRST in the New tournament drawer (a segmented
control, not a select; the rest of the form reshapes to the kind). The kind decides:

| | fighters (as built) | sports | list |
|---|---|---|---|
| Entrants | members sign up, guests by hand | teams / schools / players from the feed (or typed), each with `ext_source`+`ext_id` when matched | plain names typed by the organiser |
| States | draft → signups → check_in → seeding → (pools) → running → complete | draft → seeding → running → complete (no sign-ups, no check-in) | draft → seeding → running → complete |
| Who decides a set | players report, opponent confirms, TO overrides | the feed, or staff by hand; never members | members vote (timed) or the organiser decides — `decide_by` |
| Score on a set | games in a best-of | points / series wins from the feed | votes a–b |
| Members do | play | fill a pick sheet, watch the leaderboard | vote |
| Formats | all four + pools | single elimination only (the feed's shape, written as explicit links) | single, double, round robin, Swiss (single is the default) |
| Thread | #knuck-up thread, set cards with Report / Confirm / Dispute | same thread, cards carry the live score line, no player buttons | same thread, cards carry two vote buttons |

The organiser role, staff final say, shadow mode, the log, the words-are-keys rule, and the page's shell all stay as
they are. A fighters bracket must behave exactly as before (the existing 1,000+ bracket tests stay green untouched).

## Layer plan

| Layer | What | Schema | Branch |
|---|---|---|---|
| **K1** | `kind` + the list kind: `decide_by`, timed votes, vote buttons, the vote sweep, page + panel reshaped by kind | 103 | `brackets-kinds` |
| **K2** | `black_bloc/sports/` adapters (ESPN, henrygd NCAA, NHL, NBA, MLB, the NFL builder), the `sports_names` cache + nightly refresh, name search API, autocomplete on both doors, `ext_*` on entrants | 104 | `brackets-sports-names` |
| **K3** | Sports brackets: Import, Sync, the score poller, feed status, by-hand edits of everything, live score cards | 105 | `brackets-sports-live` |
| **K4** | Predictions: pick sheets, the lock, scoring, leaderboards (page + starter card), staff sheet edits | 106 | `brackets-picks` |

One layer at a time, each merged, gated and deployed (mode stays whatever `brackets_mode` is; the owner has it where he
wants it). K2 has no visible change except the Add entrant search; K3 is the first thing to show him live.

## K1 — kinds and the list kind

**Storage (schema 103).** `tournaments` gains `kind TEXT NOT NULL DEFAULT 'fighters'`, `decide_by TEXT` (`votes` |
`organiser`, list kind only; NULL otherwise), `vote_minutes INTEGER` (per set, from `brackets_vote_minutes` at creation).
`tournament_sets` gains `vote_opens_at TEXT`, `vote_closes_at TEXT`. New table `tournament_votes(id, tournament_id,
key, user_id, slot ('a'|'b'), at)` UNIQUE `(tournament_id, key, user_id)` — a member's vote is one row, changed in
place until the set closes. Existing rows read `kind='fighters'` through the default; a schema-102 file migrates with
nothing lost (the usual `test_a_schema_102_file_…` test).

**Moves (`brackets_moves` + a new `brackets_votes.py`).**
- `create` / `edit` take `kind`, `decide_by`; `kind` is fixed after creation (an edit refuses with a worded answer).
- For `kind='list'`: `open_signups` / `close_signups` / check-in moves refuse (`kind_has_no_signups`); `start` goes
  from `seeding`; entrants are added only by the organiser (`POST …/entrants` with a name; `user_id` always NULL); the
  Sign up / Check in / Leave / Drop out member moves are not rendered.
- `decide_by='votes'`: when a set becomes ready (start, or a feeder completes) `vote_opens_at = now`,
  `vote_closes_at = now + vote_minutes`; `vote(bot, guild, user, tournament_id, key, slot)` — any member while the set
  is open (not the organiser's call to make: anyone in the server may vote); `close_vote` (the sweep, or the
  organiser's **Close now**) tallies, writes `score_a/score_b` = the counts, decides the winner through the same path
  `override` uses (so placements, `winner_to`, cards and the log all follow), `confirmed_how='votes'`; a tie leaves the
  set `reported` with the tied words and the organiser decides (Decide modal as today). The organiser may also Decide
  before close (staff final say) — that closes the vote. `brackets_votes_visible` on → the counts show live on the card
  and the page; off → `n votes` only until close.
- `decide_by='organiser'`: the set is ready; only the organiser's Decide / forfeit / reset apply; no vote columns set.
- The vote sweep: one `Reconciler` tick a minute (as the ninja sweep), `close_due_votes` for every running list
  tournament; it runs even in shadow (the thread is the shadow home then).

**Discord.** The set card of a votes set carries two buttons labelled with the two entrants' names (clipped to 80), plus
the organiser's existing Decide / Reset. A press is an ephemeral "You voted for {name} · change any time until {closes}"
(`brackets_vote_said`). The status line reads the open words (`brackets_vote_open_line` — `{a} {votes_a} · {b}
{votes_b} · closes {closes}` or the hidden variant), then the closed words (`brackets_vote_closed_line`), tied
(`brackets_vote_tied_line`). The starter card's format line reads the kind words (`brackets_kind_list_words` etc.).
The `/bracket` panel's New tournament path (if one exists on Discord — builder verifies; the site drawer is the
known door) asks the kind first.

**Page.** The New / Edit drawer: kind control first; list kind hides best-of, pools, check-in, confirm minutes and
sign-up options, shows `decide_by` (segmented) and vote minutes. A list row in the list shows the kind pill. Set drawer
on a votes set: the two names as 40 px vote buttons with live counts, *closes in N*, the viewer's own vote marked; the
organiser gets **Close now** and Decide. Entrants section: Add entrant is a plain name box (no member picker) for the
list kind. Filters: a **Kind** chip row (All / Fighters / Sports / List) through the shared `listFilter`.

**API.** `POST/PATCH /api/brackets` accept `kind`, `decide_by`, `vote_minutes`; `POST /api/brackets/{id}/sets/{key}/vote
{slot}` (members); `POST …/sets/{key}/close-vote` (organisers); `GET /api/brackets/{id}` adds per set `votes_a`,
`votes_b`, `my_vote`, `vote_closes_at`, and on the row `kind`, `decide_by`. Contract + mock rows for each.

**Keys.** `brackets_kind_default` (`fighters`), `brackets_decide_default` (`votes`), `brackets_vote_minutes` (1440,
1–20160), `brackets_votes_visible` (on), plus the word keys named above and `brackets_kind_fighters_words` /
`_sports_words` / `_list_words`, `brackets_vote_button_change` ("Change vote"), `brackets_close_vote_label`
("Close now"). Log kinds `brackets.vote_opened` (per set, when it opens), `brackets.vote_closed` (with the counts),
`web.brackets.vote` is NOT logged per press (noise) — the count is the record.

### K1 as built (branch `brackets-kinds`, 2026-11-06) — the delta from the spec above

- **One column beyond the brief:** `tournament_sets.vote_closed_at`. Without it a vote whose time has passed but
  that the sweep has not closed yet looks the same as one a Reset brought back; `store_.sync_votes` is the one place a
  vote opens (fresh ballots), closes or clears, by the set's state.
- **States:** a list bracket starts from `draft` (Start is legal there, as it already was for fighters); `seeding` is
  reached only by Back to seeding. Sign-up / check-in / join / entrant check-in refuse with
  `brackets_kind_has_no_signups_said` (`no_signups`, 409). An entrant added with a member id is stored as a plain name.
- **Sets:** a list bracket is forced to Bo1 and no pools on every create and edit. Its score is a COUNT:
  `play.override(free=True, how=...)` skips the best-of check; the named side wins, else the higher count; level with
  no pick is `pick_winner` (400, organiser words). The vote close, the organiser's Decide and the Discord pick form all
  go through `brackets_sets.overridden` — the one winner-writer. A tie is written as `reported` with the counts (no
  winner) and the confirm sweep skips list brackets so it cannot "stand".
- **The organiser's Decide** on a list set is two buttons, one per name (`{name} wins` — page; `{name} wins…` + reason
  form — Discord), not a score picker; on a voted set it keeps the vote's counts as the score.
- **The sweep:** `brackets_votes.close_due_votes` runs inside the existing one-minute `brackets_thread.sweep` (the cog's
  `Reconciler` tick), skipped only while `brackets_mode` is `off`. An unreadable closing time is due at once.
- **Discord create (NOT built, flag to the owner):** the `/bracket` home view is pinned by the existing panel tests
  (its labels and the four-format dropdown), and the hard rule kept those tests untouched, so a list bracket is made on
  the site only. Once made, the panel runs it: Start from draft, *Add a name…*, and on a set the vote buttons, the picks
  and Close now.
- **API:** `GET /api/brackets` adds `kind_defaults` (`kind`, `decide_by`, `vote_minutes`) beside `defaults` (left exactly
  as it was) and per row `kind`, `decide_by`; a set row adds `votes_a`, `votes_b` (None while hidden and open),
  `vote_count`, `my_vote`, `vote_opens_at`, `vote_closes_at`, `vote_open`.
- **Keys:** 20 (CORE_KEYS 393 → 413): `brackets_kind_default`, `brackets_decide_default`, `brackets_vote_minutes`,
  `brackets_votes_visible`, and 16 words — the three kind names, the two decide names, `brackets_vote_said`,
  `_vote_open_line`, `_vote_hidden_line` (the hidden variant), `_vote_closed_line`, `_vote_tied_line`,
  `_vote_button_change` (the other name's hint on the page once you voted), `_close_vote_label`,
  `_kind_has_no_signups_said`, `_vote_not_open_said`, `_not_votes_said`, `_vote_pick_said`. Organiser-only lines
  (`kind_fixed`, `sports_not_yet`, `pick_winner`, the pick label) are constants (the owner's "bb").
- **Log kinds:** `brackets.vote_opened` (bare kind from either door), `brackets.vote_closed` (and `web.` twin from Close
  now on the site; details `votes_a`, `votes_b`, `tied`). A press is not logged.
- **Page filters:** the Kind chip row goes through the shared `listFilter` — which gained an optional `groups` (a second
  chip row that ANDs with the first; `listfilter.js` `passes`), fixtures in `site/mock/listfilter.test.mjs`.

## K2 — the sports package, names and autocomplete

**Package `black_bloc/sports/`** (pure adapters, no Discord, no bracket knowledge beyond the `Bracket` shape):

| File | Does |
|---|---|
| `model.py` | `League` codes `nfl nba mlb nhl ncaam ncaaw`; `Team(ext_id, name, short, league)`, `Player(ext_id, name, team_ext_id, league)`, `Game(ext_id, source_key, a_ext_id, b_ext_id, a_score, b_score, status live/final/scheduled, starts_at, period_words)`, `Bracket(league, season, games[], links{source_key → (next_source_key, slot)}, seeds{ext_id → seed}, best_of{source_key → n})`, `Found(ok, why, value)` |
| `http.py` | one `aiohttp` session, `User-Agent: Mozilla/5.0 (Black Bloc)`, 15 s timeout, per-host minimum interval (henrygd 3/s → 400 ms), every call answers `Found`, never raises; `TEST_MODE`-style guard so tests never touch the network |
| `espn.py` | scoreboard (all six leagues; `groups=100` for the NCAA tournament; `seasontype=3` for playoffs), `/teams` lists, rosters/athletes, standings `playoffSeed` (NFL), player search `common/v3/search?type=player` |
| `ncaa.py` | henrygd `/brackets/basketball-{men,women}/d1/{year}` → `Bracket` (67 games, `bracketPositionId` → `victorBracketPositionId` + top/bottom = the links), `/schools-index` |
| `nhl.py` | `playoff-bracket/{yr}` → `Bracket` (series letters, seeds, `topSeedWins/bottomSeedWins`, `winningTeamId`); NHL player search as the live fallback |
| `nba.py` | `stats.nba.com/stats/playoffbracket` → `Bracket` (series + play-in), with the `Referer`/`Origin` headers; scores from ESPN (cdn.nba.com is 403 from Fly); `playerindex` for names |
| `mlb.py` | `schedule/postseason/series` → `Bracket` (per-series `best_of` 3/5/7/7), `sports/1/players`, `people/search` |
| `nfl.py` | no feed bracket exists: builds the 14-team bracket from ESPN `playoffSeed` (7 per conference, the 1 seed's bye, **reseeding** — after each round the highest remaining seed hosts the lowest), results from the ESPN scoreboard; the links for rounds 2+ are resolved as rounds complete |
| `feeds.py` | `feed_for(league)` → primary + fallback adapters; `bracket(league, season)`, `scores(league, day)`, `teams(league)`, `players(league)`; a primary's failure falls through to the fallback and the answer names which one answered (`via`) |

Season labels are normalised in each adapter (ESPN `2027` = NBA/NHL 2026-27; NHL `20262027`; NBA `2026-27`).

**Names cache (schema 104).** `sports_names(id, kind team|school|player, league, source, ext_id, name, short, aliases,
team_ext_id, updated_at)` UNIQUE `(source, kind, league, ext_id)`; index on `(kind, league, name)`. Refresh: one
`Reconciler` sweep at `brackets_names_refresh_hour` (4, Phoenix) refreshes every list (teams for all six, schools, players
for the four pro leagues from rosters — NFL from `/teams/{id}/roster`, not the 20k athletes list); `POST
/api/sports/refresh` (staff) runs it now; `GET /api/sports` shows per list the row count and `updated_at`. Log kind
`sports.names_refreshed` (counts) / `sports.names_failed`. A few thousand rows; one SQL `LIKE` prefix + substring search
through the shared search rules (the one-search-module rule for the page side).

**Entrants (schema 104).** `tournament_entrants` gains `ext_source TEXT`, `ext_id TEXT`, `short TEXT`. A matched entrant
keeps the feed's id; a typed name has NULLs and the feed can never fill its results (the page says *typed — results by
hand* on it). An organiser may edit name / short / ext id / seed on any entrant at any time (page row editor + the panel's
Edit entrant modal) — the owner's by-hand rule.

**Search.** `GET /api/ref/sports?kind=team|school|player&league=&q=` → ≤25 `{ext_id, name, short, league, team}`
(members may read it — it is public data, unlike `/api/ref/members`). Page: the Add entrant box on a sports bracket is a
typeahead over it (kind + league chips above), Enter on a result adds the matched entrant, Enter on no result adds the
typed name. Discord: the organiser's **Add entrant** on the panel opens a modal (one name box); the bot answers with an
ephemeral select of the closest 25 matches plus *Use "{typed}" as typed*. No new slash command (the panels rule;
Discord modals have no autocomplete).

### K2 as built (branch `brackets-sports-names`, 2026-11-06) — the delta from the spec above

- **Shapes beyond the table:** `Team` carries `aliases` (ESPN's short name, location and nickname; henrygd's long
  school name) so a search for *Celtics* or *University of Connecticut* finds the row; `Player` carries `short`
  (ESPN `shortName`); `Bracket` carries `names` (ext id → display name) for K3's Import; `Game` carries `round`.
  `Found` has `via`. Sources are `espn`, `ncaa` (henrygd), `nhl`, `nba`, `mlb`.
- **Which source answers what (`feeds.FEEDS`):** teams — ESPN for all six (MLB falls back to statsapi); players —
  ESPN rosters for the four pro leagues (NBA falls back to `playerindex`, MLB to `sports/1/players`; NFL and NHL have
  none); schools — henrygd; brackets — henrygd (NCAA), NHL, stats.nba.com, statsapi, the NFL builder over ESPN, with
  **no fallback** (assembling an NCAA bracket from ESPN's `groups=100` scoreboard is left to K3); scores — ESPN for
  all six, falling back to henrygd (NCAA), NHL `score/{day}` and statsapi (MLB); none for NBA (cdn.nba.com is 403
  from Fly) or the NFL. ESPN's live player search was **not built** (nothing calls it; the local cache is the design).
- **Words, not statuses:** a feed refusal reads *had nothing at that address* / *refused the request* / *asked Black
  Bloc to slow down* / *had a server error*, a timeout *did not answer in time*, else *could not be reached*, each
  prefixed with the source and suffixed with what was asked (*ESPN had a server error for the NHL roster of team 2*).
- **Lists and refresh:** 11 lists (teams × 6, schools, players × 4). A list is replaced only when every call for it
  answers; names a feed stops sending are kept (an entrant may point at one). The sweep is the new `Sports` cog
  (10-minute `Reconciler` tick): never while `brackets_mode` is off; at once when the table is empty (a fresh deploy
  does not wait for 4 am); else once a local day from the hour when the newest row is 20 h old — so a bot that was down
  at 4 catches up, and a failing day is tried once, not every tick. The failure streak lives in memory on the bot.
- **Website refresh:** runs behind the answer (one at a time); the route waits 8 s and says either *Names refreshed:
  N of 11 lists answered.* or that it is running. Log rows: `web.sports.refresh` (the press), `sports.names_refreshed`
  and `sports.names_failed` (consequences, bare kind — checklist 34). A new head `sports` (core).
- **Entrants:** list AND sports entrants never keep a member id. `GET /api/brackets/{id}` adds `ext_source`,
  `ext_id`, `short`, and `ext_league` / `ext_name` (the names row the id points at). A matched add with no name takes
  the feed's name and short. `PATCH …/entrants/{id}` takes any of name / short / seed / ext pair, at any state.
- **Search answer** carries `kind` beside `{ext_id, name, short, league, team, source}`; schools have `league` `''`.
- **Discord:** the closest **24** names (across teams, schools and players) plus *Use "…" as typed* — 25, Discord's
  option cap (checklist 40); no match adds the typed name at once. **Edit entrant** shows on sports and list entrants
  only — the fighters entrant view's buttons are pinned by the existing panel tests (flag to the owner).
- **Page:** the typeahead is `ui.js` `remoteSearch` (the shared module's server-backed sibling of `listFilter`); the
  inline **Edit entrant** is on sports and list rows; a staff **Sports names** section on the tournament list (per
  list: names, updated, last failure; **Refresh now**). The mock seeds sports bracket **21** (*NBA Playoffs 2027*,
  seeding, one matched and one typed entrant). `sports` create stays refused (`sports_not_yet`) until K3.
- **Keys:** 12 (CORE_KEYS 413 → 425): `brackets_names_refresh_hour`, the six `brackets_league_*_words`,
  `brackets_typed_entrant_note`, `brackets_edit_entrant_label`, `brackets_entrant_edited_said`,
  `brackets_ext_unknown_said`, `brackets_use_typed_label`. The page's own organiser labels (Teams / Schools / Players,
  Short name, Clear match, Sports names, Refresh now) are constants (the owner's "bb").

## K3 — sports brackets live

**Storage (schema 105).** `tournament_sets` gains `source_key TEXT`, `scheduled_at TEXT`, `live_status TEXT`,
`period_words TEXT`, `decided_by TEXT` (`feed` | `staff` | NULL), `held INTEGER NOT NULL DEFAULT 0` (a staff edit sets
it; the poller never writes a held set). `tournaments.source` takes `espn | ncaa | nhl | nba | mlb | own` (the column
exists; `startgg` stays reserved), `source_ref` = `{league}:{season}`, new `league TEXT`, `season TEXT`,
`feed_ok_at TEXT`, `feed_failed_at TEXT`, `feed_failures INTEGER NOT NULL DEFAULT 0`, `feed_error TEXT`.

**Create.** Kind sports → league (segmented, six), season (default: the current one per adapter), source auto from the
league (`feed_for`) or **By hand** (`source='own'`). The format is single elimination; third place off; best-of is per set
from the feed (series) or 1 (games).

**Import** (organiser move, in `seeding`; `POST /api/brackets/{id}/import`): `feeds.bracket(league, season)` → entrants
(teams with `ext_*`, `seed`), sets written DIRECTLY with explicit `winner_to` / `winner_slot` links, `best_of`,
`source_key`, `scheduled_at` — not through the engine's power-of-two builder (play-in / First Four are round 0 sets
feeding a round-1 slot; byes are sets with one slot filled and `state='bye'`). **Builder verifies first** that
`brackets/play.py` advances by the stored links and never recomputes shape from the entrant count; if it does, the
sports path gets its own small `brackets/sports_shape.py` walker and the pure engine stays untouched. Before the start,
Import again replaces everything; after the start **Sync** only fills results and times. With no feed (`own`, or a
feed that fails on Import) the organiser builds it by hand: add entrants with seeds, **Build bracket** (single
elimination with byes, the normal engine), then edits times and results as they come.

**The poller** (`sports_sync`, a `Reconciler` sweep): every `brackets_sync_seconds` (60) while a running sports bracket
has a set `live` or `scheduled_at` within 15 minutes; otherwise every `brackets_sync_idle_minutes` (60). One feed call
per league per tick covers every bracket of that league. For each set: match by `source_key`, else by the unordered pair
of `ext_id`s on that day; write `score_a/score_b`, `live_status`, `period_words`, `scheduled_at`; on final → decide
through the override path with actor `feed` (`decided_by='feed'`), which advances `winner_to`, writes placements,
re-renders cards and logs `brackets.feed_result`; a held set is skipped. NFL: when a round completes, `nfl.py` resolves
the next round's links (reseed) before results are matched. A feed failure (primary and fallback) sets
`feed_failed_at`, bumps `feed_failures`, logs `brackets.feed_failed` once per streak (like the Bluesky mirror), and the
page / starter card say *feed down since {when} — results by hand* (`brackets_feed_down_line`); recovery clears it and
logs `brackets.feed_back`. Staff **Sync now** on the page and panel.

**By hand (the owner's rule).** Every set: Decide with scores (exists), **Edit** time / score line without deciding
(new: `PATCH …/sets/{key}` with `scheduled_at`, `score_a`, `score_b`, `live_status`), Reset (exists); each sets
`decided_by='staff'`, `held=1`, with a reason, DM'd nowhere (teams are not members). Every entrant: edit name / short /
seed / ext id, add, remove, swap into a slot before the start. The structure: Import, Build bracket, or edit a set's
slots before the start (`PATCH …/sets/{key}` with `slot_a`/`slot_b`, organisers, `seeding` only). **Release hold**
puts a set back under the feed.

**Page and cards.** The bracket tree draws the score line and status on every card (*Final 78–71*, *Q3 4:12 · 55–51*,
*Sat 7:10 PM*); the head shows the league badge, the season, *via ESPN · synced 40 s ago*, or the feed-down line; the
organiser moves gain Import / Build bracket / Sync now / Edit…; the set drawer gains Edit and Release hold. The thread's
set cards carry the score line (edited on change under the existing card budget); no Report / Confirm / Dispute buttons
on a sports set; the starter card gains the league line and, once K4 lands, the leaderboard.

**Keys.** `brackets_sync_seconds` (60, 30–600), `brackets_sync_idle_minutes` (60, 5–1440),
`brackets_names_refresh_hour` (4, 0–23, Phoenix — K2), the league words (`brackets_league_nfl_words` …), the card
lines (`brackets_score_final_line`, `_live_line`, `_scheduled_line`, `brackets_feed_via_line`,
`brackets_feed_down_line`, `brackets_feed_back_line`, `brackets_typed_entrant_note`), the move labels (Import, Build
bracket, Sync now, Edit, Release hold). Log kinds `brackets.imported`, `brackets.synced` (only when something changed),
`brackets.feed_result`, `brackets.feed_failed`, `brackets.feed_back`, `brackets.set_edited`, `brackets.hold_released`,
`web.brackets.*` mirrors.

### K3 as built (branch `brackets-sports-live`, 2026-11-06) — the delta from the spec above

- **The first question, answered:** `brackets/play.py` advances ONLY by the stored `winner_to` / `winner_slot`
  (`feeds` → `deliver` → `wake`); shape is computed once, in `build`, never again. So a feed's sets are written
  directly with explicit links by a small pure `brackets/sports_shape.py` (positions, keys, places) and the engine is
  untouched. **One gap the spec did not foresee:** the engine byes a waiting set whose empty slot has no feeder, which
  would have advanced the NFL 1 seed and every NBA 1/2 seed before their opponent existed. A slot the feed has not named
  gets a *pending* feeder (a `BYE` set `pending-{key}-{slot}` with no slots, never carded, never sent to the page);
  the feed (or a staff Edit) filling the slot removes it.
- **Sync reads `feeds.bracket` for every league**, not the scores feed: the bracket call carries series wins (NHL,
  NBA, MLB), henrygd's scores (NCAA, keyed by its own slugs — ESPN's ids would not match an imported entrant), and
  for the NFL it IS the builder's resolve step (standings + every playoff week, about six HTTP requests a tick).
  `feeds.scores` is called only when a running bracket has sets with no feed key (Build by hand on a fed league),
  matched by the unordered ext-id pair on the guild's local day, and only for entrants from the answering source.
- **The poller** is a second 30 s loop on the `Sports` cog with its own `Reconciler` and `loop_health("_sync")`; the
  last read per (league, season) lives in memory, so a restart reads at once.
- **Edit after the start:** the spec allows slot edits before the start only; built, slots may also be set on a set
  with no result after the start (decision 10 below) — without it a feed that dies mid-NFL-playoffs leaves the
  divisional round unfillable. Emptying a slot gives it a pending feeder again.
- **Words:** 19 keys (CORE_KEYS 425 → 444): the 18 of the spec (`brackets_sync_seconds`, `brackets_sync_idle_minutes`,
  three score lines, three feed lines, `brackets_source_own_words`, five move labels, `brackets_reimport_asks`,
  `brackets_held_note`, the two decided-by words) plus **`brackets_no_score_words`** ("(no score)"): a set decided
  with no score read "by forfeit", which is false for a sports pick (and for a list pick with no votes — that line
  changes too). Organiser-only answers (imported, built, synced, set_edited, the refusals) are constants (`TO_WORDS`).
- **Create:** a sports create needs `league` (six codes; none → `bad_option` 400 naming them — this replaces K1's
  `sports_not_yet`, so the two K1 tests that pinned that refusal now pin this one); `season` defaults to
  `feeds.current_season`; `source` is the league's BRACKET feed (`espn` for the NFL, `nba`, `mlb`, `nhl`, `ncaa`) or
  `own`. The edit drawer can change league / season / source before the start.
- **Start** on a sports bracket with stored sets keeps them (a removed team forfeits); with none it builds through the
  engine as Build does. Set cards are not posted before the start (Import and Build write sets in draft/seeding).
- **Discord:** a sports card has `{name} wins…` x2 (optional scores), Reset… once played, Edit… (time, status, two
  scores, reason — Discord's 5 inputs; teams are edited on the site only), Release hold while held. The panel offers
  Import / Build bracket / Sync now, asking first over teams or sets. No player buttons, no DMs (teams have no member).
- **Page:** league badge, season, the feed line (*via NCAA (ncaa-api) · synced 1m ago* / *feed down since …* / *By
  hand*), Import / Build bracket / Sync now, the score line on every card's top line, a held tag, the sports set drawer
  (pick with optional scores, Reset, Release hold, an Edit fold with time / status / scores / slots). A round-0
  play-in draws in its own first column beside the slot it feeds (`bracket-layout.js` `playIn`).
- **Log kinds:** `brackets.imported`, `built`, `synced`, `feed_result`, `feed_failed`, `feed_back`, `set_edited`,
  `hold_released` (+ `web.` twins through `kind_via`); feed_back / set_edited / hold_released are IMPORTANT,
  imported / built / synced / feed_result ROUTINE, feed_failed IMPORTANT by suffix.

## K4 — predictions

**Storage (schema 106).** `tournament_picks(id, tournament_id, user_id, key, pick INTEGER (entrant id), at)` UNIQUE
`(tournament_id, user_id, key)`; `tournament_sheets(tournament_id, user_id, tiebreak INTEGER, points INTEGER, correct
INTEGER, possible INTEGER, rank INTEGER, locked_at, edited_by, edited_at, updated_at)` UNIQUE `(tournament_id,
user_id)`. `tournaments` gains `picks_lock_at TEXT` (set at Import / Build to the earliest `scheduled_at`; organiser
editable), `picks_points TEXT` (from `brackets_pick_points` at creation), `picks_on INTEGER DEFAULT 1` (sports kind only).

**Rules.** A sheet is a pick per set in the final phase (round ≥ 1); round-0 sets (play-in, First Four) score 0 by
default and are not required. Choosing a later-round pick requires the earlier pick that feeds it; changing an earlier
pick clears the later picks that depended on it (the page does this live; the API refuses an inconsistent sheet with
words). Picks are editable until `picks_lock_at`; after it, only staff **Edit sheet** (reason, logged
`brackets.sheet_edited`, the sheet marked *edited by staff*). Scoring: `points` per round from `picks_points`
(`1,2,4,8,16,32`; a shorter list repeats its last value; round 0 = 0); a pick scores when the real set completes with the
picked winner; `possible` = points still reachable (picks whose team is still alive). Tiebreak (`brackets_pick_tiebreak`
off by default): the final's total points, closest wins. Standings re-rank on every real completion and on complete are
frozen (`rank`). Sheets are private until the lock, public after it (anyone may open another member's sheet, read-only —
the "compare" in the owner's words).

**Page.** `/brackets.html#<id>`: a **My picks** tab beside the real bracket (same tree, each slot a 40 px button that
advances that entrant; the lock countdown; *saved*; the tiebreak box), a **Leaderboard** section (rank, member, points,
correct / played, possible; the viewer's row outlined; press a row → that sheet drawn over the real tree with hits and
misses coloured), and on each real-bracket card a small *your pick* mark once locked. Staff: Edit sheet from the
leaderboard row.

**Discord.** The starter card gains the top `brackets_leaderboard_rows` (5) and *N sheets in · locks {when}* before the
lock; a **My picks** button opens an ephemeral panel: the lock time, the viewer's points / rank, a link to the page's My
picks tab (`brackets_picks_link_label`), and — only while unlocked — a per-round select to pick quickly (two selects of
≤25 for a 32-game round). The full sheet is a page job; the panel is the quick path. *(Decision beyond the brief,
flag to the owner: picks live mainly on the site because a 63-pick sheet is bad UX in Discord selects.)*

**Keys.** `brackets_pick_points` ("1,2,4,8,16,32"), `brackets_pick_tiebreak` (off), `brackets_leaderboard_rows` (5,
0–25), words: `brackets_picks_lock_line`, `_locked_line`, `_my_picks_label`, `_leaderboard_heading`,
`_sheet_edited_note`, `_picks_link_label`, `_pick_saved`, `_pick_too_late`. Log kinds `brackets.picks_locked` (one per
tournament, by the sweep at the lock), `brackets.sheet_edited`, `web.brackets.sheet_edited`; a member's own pick presses
are not logged.

## Decisions beyond the brief (for the owner, flagged when each layer lands)

1. Anyone in the server may vote on a list bracket, not only entrants (a candy-bar bracket has no entrants).
2. A vote tie goes to the organiser (the set waits `reported` with the tied words) rather than a coin flip.
3. Sports brackets never use Report / Confirm — teams are not members; staff and the feed decide.
4. A staff edit holds a set against the feed until **Release hold**; the feed never overwrites a human.
5. The full pick sheet lives on the site; Discord gets the leaderboard, a quick per-round select and the link.
6. Sheets are private until the lock, public after it.
7. Round-0 games (play-in, First Four) score 0 by default.
8. NBA live scores come from ESPN (cdn.nba.com is 403 from Fly, measured); NBA series shape from stats.nba.com.
9. No paid feed; the by-hand path is the fallback of last resort (owner's Q4).
10. (K3) A set's teams may be edited after the start while it has no result, so a dead feed never strands a round
    the feed would have named (NFL reseed, NBA play-in).
11. (K3) A set decided with no score reads "(no score)" (`brackets_no_score_words`), on list sets too, rather than
    "by forfeit".

## Not built (unless asked)

CFB playoff (12 teams; an adapter later), soccer, logos or images (names only — terms), odds, a start.gg mirror (still
only the `source` column), pools for the sports kind, a public leaderboard across tournaments (season-long points), the
women's NCAA tournament beyond the same henrygd path (`basketball-women` — it is in K2/K3 as a league, nothing extra).

## Build rules for every layer (put in each brief)

- Worktree at `C:/lcw/bb-<branch>` off `main`; commit at clean boundaries and often; `pull --rebase --autostash`;
  explicit `git add`; never `git stash`; never `git add -A`.
- `docs/info/review-checklist.md` (47 items) before the gate; `pytest -q -n auto` green; ruff line 100 (pre-existing
  format diffs ignored); `check.mjs`; the contract + the mock for every new route; tests mirror the package.
- Near-zero comments; every posted word a settings key (registry + mock row + label); no explaining blurbs; channel
  pickers through the shared helper; search through the shared module; a person never sees a bare HTTP status.
- The existing fighters tests stay untouched and green; a schema-N file migrates with nothing lost (test it).
- The network is never touched in tests (`sports/http.py` guard); fixtures are trimmed real responses saved under
  `tests/sports/fixtures/` (field names only, a few games — no bulk copies).
- Report: what was built, what was verified, what was NOT, decisions beyond the brief, the direct review links.

## Gate — K1 (2026-11-06, branch `brackets-kinds`, code at the commit that adds this section)

| Check | Result |
|---|---|
| `pytest -q -n auto` | **14,183 passed, 1 skipped, 0 failed** (baseline on `main` `a4c828db`: 14,126 passed, 1 skipped, 1 failed — `test_golive.py::test_the_second_platform_is_an_edit_and_never_a_second_ping`, which passes alone; not touched here and green in this run) |
| existing bracket tests | untouched (0 removed or changed lines in `tests/test_brackets_*.py`, `tests/brackets/`, `tests/api/tools/test_brackets.py`) and green; changed outside them: the schema-version literals in `tests/storage/test_db.py` (102 → 103), the key counts in `tests/test_settings_store.py` (393 → 413, 1309 → 1329), one kind added to `tests/test_logkinds.py`'s known dynamic list |
| schema 102 → 103 | `tests/storage/test_db.py::test_a_schema_102_file_gains_bracket_kinds_and_votes_and_loses_nothing` (a fighters tournament and a played set survive, `kind` reads `fighters`, twice-connect) and `::test_one_vote_per_member_and_set_is_the_databases_rule` |
| `ruff check .` | clean |
| every `site/public/assets/*.js` parses as a module; the deploy gate's 14 `site/mock/*.test.mjs` | all ok (`brackets.test.mjs` +5 list cases, `listfilter.test.mjs` +3 group cases) |
| `node site/mock/check.mjs` against the mock | ok — 28 pages, 386 routes, 413 core settings (3 new routes: the list create, vote, close-vote) |
| the page on the mock, by eye (1512 px) | list chips filter, kind pills, the drawer reshaped by List (decide-by + vote minutes, no game / best-of / cap / check-in), a vote marking the button and moving the count, Close now → *Tied 2–2 · an organiser decides*, Reset → a fresh vote, a list create + start from draft, sports refused in words |

**Checklist items that bit:** 6 (votes under the tournament lock + the unique index), 5 (an unreadable close time is due), 15
(one winner-writer — the vote close reuses `overridden`), 33 (every new default a key; a list bracket's own
`decide_by` / `vote_minutes` are editable on the page — **not** on Discord, which has no create or edit for the list
kind), 34 (Close now on the site leaves one `web.brackets.vote_closed` row; no `note()` in the route), 36 (the pick form
is a `SetForm`, so it carries `previous`), 37 (the close runs inside the existing `Reconciler` tick), 39 (the pick form's
title is clipped to 45), 11 (list cards ping nobody: entrants have no user id).

**NOT verified:** nothing ran against real Discord (the vote buttons, the pick form, a card edit per vote press — a busy
vote edits its card on every press and leans on the existing `card_failed` retry for rate limits); the phone width
(< 700 px) of the drawer was not looked at; the real server's sweep closing a vote was exercised only through tests
(`test_the_sweep_closes_a_due_vote_and_the_card_reads_the_result`), never on Fly.

## Gate — K2 (2026-11-06, branch `brackets-sports-names`, code at `743f61b6`)

| Check | Result |
|---|---|
| `pytest -q -n auto` | **14,305 passed, 1 skipped, 0 failed** (baseline on `main` `481a509b`: 14,182 passed, 1 skipped) |
| existing tests | untouched except literal bumps: `tests/storage/test_db.py` schema 103 → 104 (19 literals), `tests/test_settings_store.py` key counts (413 → 425, 1329 → 1341), `tests/test_logkinds.py` (`entrant_edited` in the bracket kinds, `web.sports.refresh` in the route-note list, `sports.%` / `web.sports.%` in the core heads). Support added, nothing removed: the network guard in `tests/conftest.py`, `WebBot.sports_fetch` in `tests/api/conftest.py`, a sports seed in `tests/api/test_contract.py` |
| schema 103 → 104 | `tests/storage/test_db.py::test_a_schema_103_file_gains_sports_names_and_entrant_ext_ids_and_loses_nothing` (twice-connect) and `::test_one_name_per_source_kind_league_and_id_is_the_databases_rule` |
| `ruff check .` | clean |
| every `site/public/assets/*.js` parses as a module; the deploy gate's 14 `site/mock/*.test.mjs` | all ok |
| `node site/mock/check.mjs` against the mock (port 8917) | ok — 28 pages, 391 routes (+5), 425 core settings |
| fixtures | 19 trimmed real responses under `tests/sports/fixtures/`, fetched once 2026-11-06 ~19:30 Phoenix from the owner's machine (ESPN teams/rosters/scoreboards/NFL standings and the whole 2025 NFL postseason, henrygd 2026 men's bracket/schools/scoreboard, NHL 2026 bracket/scores, NBA 2025-26 bracket and player index, MLB 2026 postseason/teams/players/schedule); the largest is 16 KB |
| the page on the mock, by eye (1512 px) | `/brackets.html#21`: *sp* offers the Spurs and *Use "sp" as typed*; Enter adds the Spurs (SA · NBA) and the box keeps focus; *Zorbs* + Enter adds it typed with the note; Edit entrant on *Bobcats* re-picked *car* → Carolina Hurricanes, short filled CAR, Save; the list view's Sports names table and Refresh now |

**Checklist items that bit:** 5 (an unreadable names stamp is stale), 6 (one refresh at a time — the lock and the task —
and the `sports_names` unique index), 7 (transport errors become words at `sports/http.py`, explicit 15 s timeout), 9
(`/api/sports` shows per list the last success and the standing failure), 34 (`web.sports.refresh` is the press;
`sports.names_*` keep their bare kind; one `brackets.entrant_edited` row per edit), 37 (the sweep runs in a
`Reconciler` and marks the day before refreshing), 39/40 (the edit modal's title clipped to 45; 24 matches + 1 typed
choice = Discord's 25), 45 (the names search is word-based, in any order — found in review, fixed before the gate),
33 (`brackets_names_refresh_hour` is a key). The owner's no-bare-status rule: every feed refusal is a sentence.

**NOT verified:** nothing ran against the live feeds from this code (the fixtures are real, the requests are not);
the 124 roster calls a nightly refresh makes were not timed; nothing ran against real Discord (the SportsPick select,
the Edit entrant modal); the phone width (< 700 px) of the typeahead and the inline editor was not looked at; NBA
play-in series were empty in the probe, so their parse is unexercised; MLB's fallback links are the 2026 shape only.

## Gate — K3 (2026-11-06, branch `brackets-sports-live`, code at `0e9d93af`)

| Check | Result |
|---|---|
| `pytest -q -n 4` | **14,378 passed, 1 skipped, 0 failed** (baseline: K2's gate, 14,305 passed, 1 skipped) |
| existing tests | untouched except literal bumps: `tests/storage/test_db.py` schema 104 → 105 (20 literals), `tests/test_settings_store.py` (425 → 444, 1341 → 1360), `tests/test_logkinds.py` (8 bracket kinds in the `brackets_moves` dynamic list), and the two tests that pinned K1's `sports_not_yet` (`tests/test_brackets_votes.py`, `tests/api/tools/test_brackets.py`) now pin the no-league refusal (`bad_option`, 400). `tests/sports_fakes.py` gained the NHL bracket route |
| schema 104 → 105 | `tests/storage/test_db.py::test_a_schema_104_file_gains_the_sports_live_columns_and_loses_nothing` (twice-connect) |
| `ruff check .` | clean |
| every `site/public/assets/*.js` parses as a module; the 14 `site/mock/*.test.mjs` | all ok (`brackets.test.mjs` + the sports cases) |
| `node site/mock/check.mjs` (port 8931) | ok — 28 pages, 398 routes (+7), 444 core settings |
| the page on the mock, by eye (1512 px) | `#22` live bracket (play-in column, *Final 78–71*, *2nd 4:12 · 55–51*, *via NCAA (ncaa-api) · synced 1m ago*, Sync now); `#23` feed down (*feed down since … — results by hand*, W1-1 *held by hand*, the drawer, Release hold → *W1-1 is back under the feed.*); `#24` Import fills four teams and three sets |

**Checklist items that bit:** 6 (every write under `lock_for`, the feed call never inside it; Import re-checks after
the call), 7 (feeds already answer `Found`), 9 (`loop_health("_sync")`, the feed line on page and card), 15 (one
winner-writer: the feed decides through `overridden`), 28 (`_sync.error` restarts the loop), 33 (both cadences are
keys), 34 (the feed's rows go through `note` with `via`), 37 (the poller runs in a `Reconciler`), 39 (the Edit
modal's labels ≤ 45), 41 (a corrected final from the feed re-decides a feed-decided set), 43 (`feed_failed_at` is set
only when a streak starts, never overwritten by the next failure).

**NOT verified:** nothing ran against a live feed or real Discord; the NBA play-in and the MLB bye teams were never
in a probe, so how they import is reasoned, not seen (pending feeders should hold their slots); the NFL reseed was
exercised from the recorded 2025 postseason only; the 60 s cadence's load on ESPN during an NFL playoff weekend (six
requests a tick for the NFL bracket) was not measured; the phone width of the new drawer was not looked at; a series
league's live line shows series words (*TBL leads 3-2*), not the game in progress.
