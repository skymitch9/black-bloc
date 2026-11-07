# Sports brackets: data sources for live scores, team/school names and player names (research, 2026-11-06)

> **Audience:** Claude sessions and the owner. **Status:** TRACKED, research only. Nothing here is a decision.
> **Last verified: 2026-11-06.** An Opus research agent ran Python `urllib` probes from the owner's Windows machine,
> about 2026-11-06 17:30-17:55 Phoenix (2026-11-07 00:30-00:55Z). Every status code, latency and field name below
> comes from those probes. Latency is one sample per URL from a residential connection, not from Fly.io.
> **Checked:** the ESPN site/core/search endpoints, henrygd ncaa-api, data.ncaa.com, MLB statsapi, NHL api-web/search,
> NBA cdn.nba.com and stats.nba.com, TheSportsDB v1 (key `123`), Wikidata search and SPARQL, and the Wikipedia parse API.
> Pricing pages were read for TheSportsDB, balldontlie, henrygd's README, CollegeFootballData and the-odds-api, and the
> MLBAM copyright notice was read.
> **NOT checked:** any keyed API. balldontlie, API-Sports, SportsDataIO, MySportsFeeds, Sportradar, CFBD and the-odds-api
> were reached only far enough to see the 401/403 that a missing key returns. The API-Sports pricing page returned 403.
> Not read: ESPN/Disney terms of use (404 at the URL tried), NBA.com and NHL.com terms. No endpoint was polled over time,
> so the live update cadence is inferred from `Cache-Control` headers, not watched. Nothing was called from Fly.io.
> Secret NAMES only (none here).

Context: the fighting-game engine is in [`brackets-design.md`](brackets-design.md) (tables `tournaments`,
`tournament_entrants`, `tournament_sets`, with `tournaments.source`/`source_ref` already reserved for an outside feed).
start.gg research: [`brackets-research-2026-10-07.md`](brackets-research-2026-10-07.md).

## Summary (one screen)

| Need | Primary | Fallback | Why |
|---|---|---|---|
| **NCAA tournament bracket** (structure + seeds + live scores) | **henrygd ncaa-api** `/brackets/basketball-men/d1/{year}` (wraps NCAA.com) | **ESPN scoreboard** `groups=100` per date (seed = `curatedRank.current`, region/round in `notes[].headline`) | henrygd has every game's `bracketPositionId` → `victorBracketPositionId`. That link is the slot map. ESPN has no bracket endpoint. |
| **NBA / NHL / MLB playoffs** | The league's own free API: NHL `playoff-bracket/{yr}`, NBA `stats.nba.com/stats/playoffbracket`, MLB `schedule/postseason/series` | ESPN scoreboard (`seasontype=3`) | Each official API returns series with seeds and wins. ESPN returns games only. |
| **NFL playoffs** | **ESPN** scoreboard (`seasontype=3`) + standings (`playoffSeed`) | TheSportsDB (paid $9 for 2-min livescore) | No free official NFL API exists. ESPN is the only free source that worked. |
| **Live/final scores, regular season** | **ESPN** `site.api.espn.com/.../scoreboard`: one shape for all five leagues | League official APIs (MLB/NHL/NBA cdn) | ESPN answered in 80-210 ms and returned in-progress games at the time of the probe. |
| **Team / school names** | **Local cached lists** from ESPN `/teams` (NBA 30, NCAAM 362, NCAAW 362, CFB 762) + henrygd `/schools-index` (1,173 schools) | MLB/NHL official team lists | These are small, static lists. Autocomplete should not call out per keystroke. |
| **Player names** | **Local cached roster lists** per league (ESPN core `athletes`, NBA `playerindex` 525, MLB `sports/1/players` 1,560, NHL search) | Live search: ESPN `common/v3/search?type=player`, NHL `search.d3.nhle.com`, MLB `people/search` | ESPN reports NFL `count` 20,325, which includes inactive players under `active=true`. Live search covers the long tail. |
| **Plain template** ("best candy bar") | **No source.** The TO types the entrants. An optional one-time seed list comes from the Wikipedia parse API | Wikidata `wbsearchentities` (live search, labels + descriptions) | Wikidata SPARQL was rate-limited to **1 req/min** (429) at probe time. Snickers is typed `brand`, not `chocolate bar`, so a SPARQL class list misses items. |

Bottom line: **ESPN + henrygd + the three official league APIs, all free and keyless.** Every one of them is unofficial
or has terms that allow only "individual, non-commercial" use. A paid keyed fallback (TheSportsDB $9/mo) is worth naming,
but nothing needs to be bought now.

## Comparison table

| Source | Leagues | Bracket/series structure | Live cadence (measured `Cache-Control`) | Auth / cost | Rate limit | ToS posture | Probe 2026-11-06 |
|---|---|---|---|---|---|---|---|
| ESPN site/core API | NFL NBA MLB NHL NCAAM NCAAW CFB + more | **None**. Seeds on tournament games (`curatedRank`) and in NFL standings (`playoffSeed`) | scoreboard `max-age=10`, teams `max-age=1`, core `max-age=900` | none | undocumented | unofficial; Disney ToU not read (NOT VERIFIED) | 200 on all main routes, 80-440 ms |
| henrygd ncaa-api | all NCAA sports/divisions | **Yes**: full NCAA bracket, 67 games, positions + links | `public, max-age=60` (BunnyCDN) | none (self-host option) | **3 req/s per IP** (README) | wraps NCAA.com; README calls the public instance a demo and says to "host your own" | 200, 74-1,623 ms |
| data.ncaa.com casablanca | NCAA | per-game `bracketId`/`bracketRound` | `max-age=5` (S3) | none | unknown | NCAA's own CDN, undocumented | 200 for 2025-03-20; **404 for 2026-11-05** (path is not stable for current dates) |
| MLB statsapi | MLB, MiLB | **Yes**: `postseason/series` | `max-age=20` | none | undocumented | MLBAM: "Only individual, non-commercial, non-bulk use" | 200, 34-294 ms |
| NHL api-web | NHL | **Yes**: `playoff-bracket/{yr}` (15 series, seeds, wins) | not recorded | none | undocumented | unofficial; NHL terms NOT read | 200, 116-256 ms |
| NBA cdn.nba.com | NBA | `seriesText`, `ifNecessary` per game | none sent | none; **needs `Referer`/`Origin: nba.com` headers** | undocumented; known to block cloud IPs (NOT VERIFIED from Fly) | unofficial | 403 without headers, 200 with them |
| NBA stats.nba.com | NBA | **Yes**: `playoffbracket` (15 series + play-in) | none sent | none; same headers | known to time out cloud IPs | unofficial | `scoreboardv2` **timed out at 20 s**; `scoreboardv3`/`playoffbracket`/`playerindex` 200 |
| TheSportsDB | ~all, soccer-first | none (event lists) | 4 h cache on the free key | free key **`123`** (old `3` is **disabled**: 403 says so); $9/mo dev, $20/mo business | free 30/min, $9 100/min | own ToU not read | key 3: 403; key 123: 200 (NBA team list returned only 10 of 30) |
| balldontlie | NBA NFL MLB +; "20+" on All-Access | not seen | n/a | free 5 req/min, $9.99/mo/sport (60/min), $39.99 (600/min) | as tiers | commercial API | 401 without a key |
| CollegeFootballData | CFB (+CBBD basketball) | not seen | live only on paid | free 1k calls/mo, **no live**; $1/mo 5k live | monthly quota | Patreon-funded | 401 without a key |
| the-odds-api | US majors + many | none | n/a | free 500 credits/mo; $30/mo 20k | credits | commercial | 401 without a key |
| API-Sports | basketball, NFL, hockey, baseball, football… | per-league | NOT VERIFIED | keyed; pricing page 403 | NOT VERIFIED | commercial | 403 "Missing application key" |
| SportsDataIO / MySportsFeeds / Sportradar | all US majors | yes (paid feeds) | NOT VERIFIED | keyed, trial/paid; Sportradar trial is not for production | NOT VERIFIED | commercial licences | 401 / 401 / 403 without keys |
| Wikidata / Wikipedia | anything | n/a | n/a | none; send a descriptive `User-Agent` | SPARQL **429 at 1 req/min** during a WDQS outage | CC0 (Wikidata) / CC BY-SA (Wikipedia text) | search 200 in 226 ms; parse 200 (777 links on the chocolate-bar list) |

## Per source, measured endpoints

### ESPN (unofficial, keyless)

```
GET https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard[?dates=YYYYMMDD|YYYYMMDD-YYYYMMDD][&seasontype=3][&groups=100][&limit=N]
    sport/league: football/nfl  basketball/nba  hockey/nhl  baseball/mlb  basketball/mens-college-basketball  basketball/womens-college-basketball  football/college-football
GET https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams[?limit=1000]
GET https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{id}/roster
GET https://site.api.espn.com/apis/v2/sports/{sport}/{league}/standings          # note /apis/v2, not /apis/site/v2
GET https://sports.core.api.espn.com/v3/sports/{sport}/{league}/athletes?limit=1000&active=true   # pageSize caps at 1000; page with &page=N
GET https://site.web.api.espn.com/apis/common/v3/search?query=mahomes&type=player|team&limit=5
GET https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/tournaments/22   # "NCAA Mens Final 4 Tournament"
```

| Probe | Status | ms | What it showed |
|---|---|---|---|
| NBA scoreboard | 200 | 137 | 9 events, states `pre`/`in`, `season {type:2, year:2027}` (ESPN labels the 2026-27 season by its end year) |
| NFL scoreboard | 200 | 116 | 15 events, week 9ish (`season.type 2, year 2026`), states `post`/`pre` |
| NHL scoreboard | 200 | 79 | 3 events, one `in` (Sabres 2-1 Blue Jackets at the time of the probe) |
| MLB scoreboard | 200 | 80 | 1 event, `season.type 3`: the last World Series game, Brewers 4 at Rays 1, Final, 2026-10-29 |
| NCAAM scoreboard `groups=50&limit=400` | 200 | 165 | 72 games tonight (season openers) |
| NCAAM 2026-03-19 `groups=100` | 200 | 212 | 16 tournament games; `type.abbreviation "TRNMNT"`, `tournamentId 22`, `notes[0].headline "NCAA Men's Basketball Championship - East Region - 1st Round"`, competitor `curatedRank.current` = seed (Duke 1 v Siena 16) |
| MLB `seasontype=3&dates=20261020-20261105` | **400** | 141 | "Failed to get events endpoint." A date range plus seasontype is refused here. |
| NBA `dates=20260601-20260630` | **400** | 185 | the same error. Use single dates. |
| NFL `seasontype=3&dates=2026` | 200 | 408 | 100 events with mixed season types (1, 2 and 3). **Filter on `season.type == 3` yourself.** |
| guessed bracket route `site.web.api.espn.com/apis/v2/.../tournament/bracket` | **404** | 180 | no bracket endpoint found |
| core `.../tournaments/22/seasons/2026/bracketology` | 200 | 185 | `count: 0`. Empty in November. |
| teams: NBA / NCAAM / NCAAW / CFB | 200 | 136-273 | 30 / 362 / 362 / 762 teams; 1.4-1.9 MB each because of logos and links |
| core athletes NFL `active=true` | 200 | 383 | `count 20325`, 1,000 per page |
| common search player / team | 200 | 224 / 415 | `items[].displayName, type, league, id, jersey, position, isActive` (Mahomes; Gonzaga in men's and women's) |
| standings NFL | 200 | 223 | `entries[].stats[].name` includes `playoffSeed` |

Shape (scoreboard): `events[].{id, date, name, season{type,year}, week, status.type{state:"pre|in|post", description, completed}, competitions[0].{type, notes[].headline, tournamentId, series, competitors[].{id, homeAway, winner, score, curatedRank.current, team{id, displayName, abbreviation, location}}}}`.

### henrygd ncaa-api (`ncaa-api.henrygd.me`, open source, wraps NCAA.com)

```
GET /scoreboard/{sport}/{division}[/{yyyy}/{mm}[/{dd}]][/{conference}]   # basketball-men/d1, football/fbs …
GET /brackets/{sport}/{division}/{year}                                   # basketball-men/d1/2026, basketball-women/d1/2026
GET /schools-index
GET /game/{id}[/boxscore|/play-by-play|/scoring-summary|/team-stats]
```

| Probe | Status | ms | What it showed |
|---|---|---|---|
| scoreboard basketball-men/d1 | 200 | 119 | 71 games; `games[].game.{gameID, gameState, startTimeEpoch, bracketId, bracketRound, home/away.{score, names, winner, seed, rank}}` |
| brackets basketball-men/d1/2025 | 200 | 1,623 | `championships[0].{title, year, games[67], rounds[], regions[]}` |
| brackets basketball-men/d1/2026 | 200 | 695 | "2026 DI Men's Basketball Championship", 67 games; the final (`bracketPositionId 701`) was Michigan (1) 69, UConn (2) 63 |
| brackets basketball-women/d1/2026 | 200 | 140 | 67 games; final: UCLA (1) 79, South Carolina (1) 51 |
| scoreboard football/fbs | 200 | 255 | live CFB |
| schools-index | 200 | 74 | list of 1,173 `{slug, name, long}` |

Bracket game shape: `{contestId, bracketPositionId, victorBracketPositionId, victorGamePosition:"Top|Bottom", gameState:"F|I|P", sectionId, isIfNecessary, teams[].{isTop, isWinner, seed, score, nameShort, nameFull, seoname}}`.
`rounds[].{roundNumber, label}` = First Four, First Round, …; `regions[].{sectionId, title, regionCode}`.
**Outside March, the previous year's bracket is served finished.** The next year's bracket is NOT VERIFIED until Selection Sunday.

### data.ncaa.com (NCAA's own S3 JSON)

`GET https://data.ncaa.com/casablanca/scoreboard/basketball-men/d1/2025/03/20/scoreboard.json` returned 200 in 717 ms
(16 games, with `bracketRound` and `bracketId`). The same path for 2026/11/05 returned **404 NoSuchKey**. henrygd is the
maintained wrapper around NCAA.com's current backend, so use it, not this path.

### MLB Stats API (`statsapi.mlb.com`, official, keyless)

```
GET /api/v1/schedule?sportId=1&date=YYYY-MM-DD&hydrate=linescore
GET /api/v1/schedule/postseason/series?season=2026&sportId=1[&gameTypes=W]
GET /api/v1/teams?sportId=1
GET /api/v1/sports/1/players?season=2026
GET /api/v1/people/search?names=judge&sportIds=1
```
All returned 200 in 34-294 ms. Today's schedule had 0 games (offseason). `postseason/series` returned 11 series; the
World Series (`gameTypes=W`) ended 2026-10-29, Brewers 4 at Rays 1. Teams: 30. Players for 2026: 1,560. The name search
returned Aaron Judge first. Every response carries `copyright` pointing at the MLBAM notice ("individual, non-commercial,
non-bulk use"). Series shape: `series[].{series{id, gameType}, games[].{gamePk, gameDate, seriesDescription, teams.{home,away}.{team{id,name}, score, isWinner, seriesNumber}}}`.

### NHL (`api-web.nhle.com`, official site backend, keyless)

```
GET https://api-web.nhle.com/v1/score/now                    # or /v1/score/YYYY-MM-DD
GET https://api-web.nhle.com/v1/playoff-bracket/2026
GET https://api-web.nhle.com/v1/playoff-series/carousel/20252026/
GET https://api-web.nhle.com/v1/standings/now
GET https://api.nhle.com/stats/rest/en/team                  # 62 rows, historical teams included
GET https://search.d3.nhle.com/api/v1/search/player?culture=en-us&limit=5&q=mcdavid&active=true
```
All returned 200 in 116-256 ms. `score/now` returned 3 games on 2026-11-06. The 2026 bracket returned 15 series:
`{seriesLetter, playoffRound, topSeedRank, topSeedWins, bottomSeedRank, bottomSeedWins, winningTeamId, losingTeamId, topSeedTeam{abbrev,…}, bottomSeedTeam}`.
Search returned `[{playerId, name, positionCode, teamAbbrev, sweaterNumber, active}]`.

### NBA (`cdn.nba.com` and `stats.nba.com`, unofficial, keyless)

```
GET https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json      # headers: Referer/Origin https://www.nba.com
GET https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json                # 7.5 MB full season
GET https://stats.nba.com/stats/scoreboardv3?GameDate=YYYY-MM-DD&LeagueID=00
GET https://stats.nba.com/stats/playoffbracket?LeagueID=00&SeasonYear=2025&State=2
GET https://stats.nba.com/stats/playerindex?LeagueID=00&Season=2026-27
```
Without the headers, cdn returned **403 Access Denied**; with them, 200. `todaysScoreboard` returned 9 games with
`{gameId, gameStatus, gameClock, ifNecessary, seriesGameNumber, seriesText, homeTeam, awayTeam}`. `scoreboardv2`
**timed out at 20 s**; `scoreboardv3` returned 200. `playoffbracket` returned 15 series:
`{roundNumber, seriesConference, highSeedId, highSeedName, highSeedRank, highSeedSeriesWins, lowSeed*, seriesWinner, nextGameId}`.
The 2026 Finals were Knicks over Spurs, 4-1. `playerindex` returned 525 rows (`PERSON_ID, PLAYER_FIRST_NAME, PLAYER_LAST_NAME, TEAM_ID`).

### TheSportsDB

The key `3` from the brief **is permanently disabled**. The 403 body said: *"The old '3' Free Sports API key is
permanently disabled, Please use the new test key "123"…"*. With `123`, `searchteams.php?t=Arsenal`,
`searchplayers.php?p=Danny_Welbeck`, `eventsnextleague.php?id=4387` and `eventsday.php?d=2026-11-05&l=4387` returned 200
(NBA, 3 FT results). `search_all_teams.php?l=NBA` returned **10 of 30** teams, which matches the pricing page's "most
queries limited". The v2 livescore route needs a header key, and livescore is on paid tiers only, updated every 2 minutes.
Fields: `idTeam, idESPN, strTeam, strTeamShort, strLeague`; `idEvent, strEvent, intHomeScore, intAwayScore, strStatus`.

### Keyed sources (not exercised; cost from pricing pages read 2026-11-06)

| Source | Free | Cheapest paid | Note |
|---|---|---|---|
| balldontlie | 5 req/min, 1 sport, "basic" | $9.99/mo/sport, 60/min | endpoints per tier not stated on the page |
| CollegeFootballData | 1k calls/mo, no live | $1/mo, 5k calls, live scoreboard | football only (CBBD shares the quota) |
| the-odds-api | 500 credits/mo | $30/mo, 20k | has a scores endpoint; odds-first, wrong fit |
| API-Sports | NOT VERIFIED (page 403) | NOT VERIFIED | |
| SportsDataIO, MySportsFeeds, Sportradar | trials | commercial pricing | overkill for one hobby server |

## Name autocomplete

Discord autocomplete must answer within **3 s** (Discord's interaction deadline, from memory, NOT VERIFIED today) and
fires on every keystroke. **Serve it from a local table, never from a live call per keystroke.**

| List | Source | Rows (measured) | Refresh |
|---|---|---|---|
| NBA / NFL / MLB / NHL teams | ESPN `/teams` (or league APIs) | 30 / 32 (not measured) / 30 / 32 (not measured) | yearly, plus on relocation or rename |
| NCAA D1 men's / women's basketball | ESPN `/teams?limit=1000` | 362 / 362 | yearly (Oct) |
| CFB teams | ESPN | 762 (all divisions) | yearly |
| Schools | henrygd `/schools-index` | 1,173 | yearly |
| NBA players | `playerindex` | 525 | daily in season (trades, signings) |
| MLB players | `sports/1/players?season=` | 1,560 | weekly |
| NFL players | ESPN core athletes | 20,325 by `count`. Filter to current rosters (32 × ~53 ≈ 1.7k, guess) via `/teams/{id}/roster` | weekly |
| NHL players | NHL search, or team rosters (not probed) | NOT VERIFIED | weekly |

- Store the list as one table (`sports_names(kind, league, ext_id, name, short, aliases)`) and match by prefix and
  substring with the shared search module (the one-search-module rule) for the site. A few thousand rows is tiny.
- A miss in the local list falls through to **free text**. Guests and "best candy bar" entrants are plain names, as
  `tournament_entrants.name` already allows. Optionally offer a live search behind a "search more" option (ESPN
  `common/v3/search`, NHL search, MLB `people/search`), rate-limited per user.
- Keep the feed's id (`ext_id`, e.g. ESPN team `150` = Duke) on the entrant. Live-score mapping needs it, and a
  name-only entrant cannot be matched reliably.

## Live-score polling and mapping a game to a bracket slot

| Bracket kind | Structure from | Slot key | Result from |
|---|---|---|---|
| NCAA men's/women's | henrygd `/brackets/…/{year}` | `bracketPositionId` (101…701); winner goes to `victorBracketPositionId` as `victorGamePosition` Top/Bottom | the same call (scores + `isWinner`), or the ESPN scoreboard matched by team id + date |
| NHL | `playoff-bracket/{yr}` | `seriesLetter` A-O + `playoffRound` | `topSeedWins/bottomSeedWins`, `winningTeamId` |
| NBA | `playoffbracket` | `seriesId` / `roundNumber` + `displayOrderNumber` | `seriesWinner`, `*SeriesWins` |
| MLB | `postseason/series` | `series.id` + `gameType` (F, D, L, W) | per-game `isWinner`, series wins |
| NFL | **built locally** from ESPN standings `playoffSeed` (7 per conference; the fixed reseeding rule) | seed pair per round | ESPN scoreboard `seasontype=3`, matched by team id |

- The bracket engine's `tournament_sets` already holds `slot_a/slot_b`, `winner_to/winner_slot`. A sports bracket is
  "own" structure seeded once, with `tournaments.source = 'espn'|'ncaa'|'nhl'…` and `source_ref` = the year or bracket
  id. Per set, the feed's slot key needs a home (a `source_ref` column on `tournament_sets` would be a schema change,
  not decided).
- **Cadence (proposal, not measured over time):** poll only while a game in the bracket is `in` or starts within 15
  minutes. Use 60 s for henrygd (its CDN caches for 60 s anyway) and 30-60 s for ESPN (`max-age=10`). Otherwise poll
  hourly. Results only need to be final to advance a slot.
- **Cost per bracket:** one call per poll covers the whole NCAA bracket (91 KB) or one league's day (20-270 KB from
  ESPN). March Madness's busiest day is about 16 games over about 12 h. At 60 s that is about 720 calls and about 65 MB
  of transfer a day. That is trivial for the bot, and well under henrygd's 3 req/s. Many member predictions cost
  nothing extra: compare locally.
- **Predictions:** a member's predicted bracket is a copy of the slot tree with a pick per slot. Score it against the
  real tree when a slot goes final. No feed call is needed per member.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| **Unofficial endpoints change or break** (ESPN, NBA, NHL, henrygd). Already seen: TheSportsDB's key `3` is dead, data.ncaa.com's dated path 404s for current dates, `scoreboardv2` hangs | high over a season | one adapter module per source behind one interface; a staff "set result by hand" move (staff-final-say) so a dead feed never blocks a bracket; log a `brackets.feed_failed` kind and alert |
| **Cloud IP blocking** (stats.nba.com and cdn.nba.com are known to block or hang datacentre IPs; not tested from Fly) | medium for NBA | prefer ESPN for NBA scores; probe from a Fly machine before relying on NBA endpoints (open question 4) |
| **Terms of service.** MLBAM allows "individual, non-commercial, non-bulk" use only; ESPN/NBA/NHL terms not read; henrygd's README calls the public instance a demo | grey for a free hobby bot; no money changes hands | no commercial use; cache aggressively; no redistribution of logos (use names only); self-host henrygd (Docker) if the demo instance becomes unreliable |
| **Rate limits.** Wikidata SPARQL was at 1 req/min; henrygd 3 req/s; ESPN undocumented | low at the planned cadence | local name lists; one poller per league, not per bracket |
| **Wrong-team matching on free-text entrants** | medium | store `ext_id`, and match by id, never by name |
| **Season labels differ** (ESPN `year 2027` for NBA/NHL 2026-27; NHL `20262027`; NBA `2026-27`) | certain | normalise in the adapter |

## Open questions for the owner

1. Which leagues first: NCAA men's March Madness only (March 2027), or NBA/NHL playoffs too (April 2027)? NFL playoffs
   start January 2027.
2. Predictions: one pick per slot scored by round (e.g. 1-2-4-8-16-32 points, ESPN style), or a different scoring?
   Lock time: tip-off of the first game, or the start of each round?
3. Should "best candy bar"-style templates ship a seed list (owner-curated, or one pulled once from Wikipedia), or stay
   free text only?
4. May an agent run a one-off probe from the Fly machine (read-only `curl` via `flyctl ssh`) to check that the NBA/NHL/ESPN
   endpoints are not blocked from datacentre IPs?
5. Self-host henrygd ncaa-api as a second Fly app (no key, about 256 MB) for reliability, or rely on the public demo plus the
   ESPN fallback?
6. Is a $9/mo TheSportsDB key acceptable as a paid fallback if the free sources break, or is the rule "free only, staff
   enter results by hand when a feed dies"?

## From the Fly machine (measured 2026-11-06 18:0x Phoenix, read-only `python3 urllib` via `flyctl ssh console`, machine 85e744c4d959d8, lax)

Open question 4 answered: the conductor ran one probe per endpoint from inside the live container, `User-Agent: Mozilla/5.0`
plus `Referer`/`Origin: https://www.nba.com` on every request, 15 s timeout.

| Endpoint | Status | Bytes | Seconds |
|---|---|---|---|
| ESPN `basketball/nba/scoreboard` | 200 | 136,933 | 0.13 |
| henrygd `/brackets/basketball-men/d1/2026` | 200 | 91,471 | 0.61 |
| NHL `/v1/playoff-bracket/2026` | 200 | 15,838 | 0.22 |
| MLB `/schedule/postseason/series?season=2026` | 200 | 57,625 | 0.23 |
| NBA `stats.nba.com/stats/playoffbracket` | 200 | 14,172 | 0.20 |
| NBA `cdn.nba.com/.../todaysScoreboard_00.json` | **403** even with the headers | — | — |

So from a datacentre IP: ESPN, henrygd, NHL, MLB and `stats.nba.com` answer; `cdn.nba.com` refuses. NBA live scores come from
ESPN; the NBA series structure from `stats.nba.com/stats/playoffbracket`. One sample each, not polled over time.
