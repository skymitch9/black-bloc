# The Run (therun.gg) — what its API lets a bot do (research, 2026-10-09)

> **Audience:** the conductor and the session that designs the BaF leaderboard / PB feed. **Status:** TRACKED, research only — nothing here is a decision and nothing was built. **Last verified: 2026-10-09** — by live GETs and one websocket session (Opus probe, 33 GETs at <=1/s, polite User-Agent, no key, no 429, no rate-limit headers) plus a desk pass (Sonnet) over public docs. ⚠️ **NOT checked:** real rate limits, write access (none found), moderator-grade verification, the real PB-update latency. Secret NAMES only (none here).
>
> The ask, verbatim (owner, 2026-10-09): *"Also check if therun.gg has an api"* then *"Can we spin up a sub agent to do test on therun.gg for now and see what we can and can't do"*. It feeds the leaderboard question set in `docs/TODO.md` ▸ Session 2026-10-09 (owner Q9: speedrun.com and The Run may be READ for data and link prefill, never auto-post PBs).
>
> ⚠️ **The probe script and trimmed raw responses live only in the session scratchpad (`probe.py`, `ws_probe.py`, `log.jsonl`, `raw\`), which is temporary and gone with the session.** They were deliberately NOT copied into the repo (owner rule: scan/research scripts never enter git). Re-run from the endpoint table below if the evidence is needed again.

## 1. Desk pass (measured = read on the day; inferred = a source's claim)

| Finding | Source | Kind |
|---|---|---|
| There is no official, documented API: `github.com/therungg/api-docs` was last touched in 2022 and says it is "still being built" | GitHub | measured |
| The frontend `.env` names `api.therun.gg` and `wss://ws.therun.gg` | `github.com/therungg/therun-frontend` | measured |
| A Node wrapper exists: `github.com/developerrowan/therun` (npm `therungg`); it warns of breaking changes. No Python wrapper | GitHub / npm | measured |
| speedrun.com changed its terms 2026-10-01 (CC BY-NC licence removed, database ownership claimed, API may be cut without notice, competing tools banned); The Run published a breakdown | one secondary article (`ecosistemastartup.com/?p=114005`) | **inferred — NOT confirmed against speedrun.com's own pages** |

## 2. Endpoints probed (all keyless, all GET)

| Endpoint | Result |
|---|---|
| `therun.gg/api/frontpagedata` | 200 `{runs, gamestats}` |
| `therun.gg/api/games` | 200, paged: 60 per page, 167 pages, 11296 items; each game carries categories with `bestTime` / `bestTimeUser` |
| `therun.gg/api/games/<slug>` | 200; `stats.categoryLeaderboards[]` with `pbLeaderboard` rows `{username, stat (ms), meta (PB date), url, placing}`. The Super Mario Odyssey response was 2.7 MB and took 5.8 s |
| `therun.gg/api/users/<name>` | 200, a list of that user's runs. ⚠️ A MISS is also 200 `[]`, indistinguishable from "no runs" |
| `api.therun.gg/users/<name>` | the same list wrapped in `{result}` |
| `api.therun.gg/users/global/<login>` | the profile, with the Twitch `login` |
| CloudFront history file (per run, `historyFilename`) | `{runs, splits, sessions, meta}` |
| Raw `.lss` splits file (`splitsFile`) | the path must be used raw — re-encoding it gives 403 |
| `api.therun.gg/live?minify=true` | 200, 58 live runs at probe time, 6 s |
| `therun.gg/api/live?limit=N` | 200 |
| `therun.gg/api/live/<user>` | `null` when the user is not live |
| `wss://ws.therun.gg` | connected; 46 `UPDATE` messages from 24 runners in 60 s. Subscribe by URL query (`?username=`, `?game=&category=`, `?race=`, `?story=`) — the filters were NOT tested |
| `api.therun.gg/games` | 502; `api.therun.gg/frontpagedata` 404 — **`api.therun.gg` does not mirror `therun.gg/api`** |

**Run fields:** `user`, `game`, `run` (the category), `personalBest` (ms, as a string), `personalBestTime` (the date), `sumOfBests`, `attemptCount`, `finishedAttemptCount`, `totalRunTime`, `pbId`, `sessions[]`, `uploadTime`, `hasGameTime`, `gameTimeData`, `historyFilename`, `splitsFile`, `url` (`therun.gg/<user>/<game>/<cat>`), `variables`, `gameregion`, `emulator`; optional `platform`, `vod`, `description`. There is no "live" flag on a run.

**LiveRun fields:** `user`, `login`, `game`, `category`, `currentSplitIndex` / `currentSplitName`, `currentTime`, `pb`, `sob`, `bestPossible`, `delta`, `currentPrediction`, `runPercentage`, `currentlyStreaming`, `hasReset`, `startedAt`, `endedAt`, `platform`, `splits[]`, `raceId`.

## 3. BaF lookups (measured 2026-10-09)

| Member | Result |
|---|---|
| Riekelt | 152 runs; `riekelt` and `RIEKELT` return the same; the global record login is `riekelt` |
| junior_sm | not on The Run (three casings -> `[]`) |
| Radgryd | `Radgryd` / `RADGRYD`: 52 runs; `radgryd`: `[]` |
| DVark09 | on the front page; `dvark09`: `[]` |

⚠️ **Case handling is inconsistent — store the exact display casing** (and never read an empty list as "this person has no runs"; it may be a casing miss).

## 4. What a bot can do

| Question | Answer | Basis |
|---|---|---|
| (a) Read a member's PBs | Usually — by exact name | measured |
| (b) Detect a new PB | Poll (the source says CDN cache 300 s per source, so up to ~5 min lag), or the websocket `?username=` within seconds while the member is live | polling lag **inferred / unmeasured** (responses said `max-age=0`, contradicting the source's 300 s); the `?username=` filter untested |
| (c) See who is live | Yes (`/live`, `/live/<user>`, websocket) | measured |
| (d) Verify a run from a link | Partly: parse `therun.gg/<user>/<game>/<cat>` and match it to that user's runs. This is not moderator verification | inferred from the fields |
| (e) Submit a time | No — no write endpoint was found | measured (absence) |

## 5. Terms — read before building a poller

`therun.gg/terms` (updated 2 Sept 2026): *"Don't scrape the site, hammer the API, or try to get around rate limits or access controls. If you want data in bulk, ask."* — **ask `info@therun.gg` before a scheduled poller goes live.** One request per member lookup at a human pace is inside the spirit; a sweep of all members on a timer is the "bulk" the terms mean.

## 6. Not determined

- The real rate limits (none were hit, none were advertised).
- Whether the websocket sends DELETE messages, and whether the `?username=` filter works.
- The real PB-update latency end to end.
- Whether the undocumented endpoints stay put (the Node wrapper warns of breaking changes).
