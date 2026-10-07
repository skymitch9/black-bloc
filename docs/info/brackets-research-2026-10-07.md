# Tournament brackets — start.gg option catalogue (research, 2026-10-07)

> **Audience:** the conductor and the session that designs the bracket engine. **Status:** TRACKED, research only — nothing here is a decision. **Last verified: 2026-10-07** — read from start.gg's help centre and developer docs by an Opus research agent on that day; nothing was tried against start.gg. Secret NAMES only (none here).
>
> The ask, verbatim (owner, 2026-10-07): *"can we also get a feature that makes fighting game tournament brackets? get all the popular configs like double elim, double elim double elim finals single elim etc"* and *"c. but start with a and yes on the finals reset, make it optional tho. check start.gg and steal all their basic tourney options"*. Decisions so far live in `docs/TODO.md`; the design doc will be `brackets-design.md`.

**The help centre is thin.** It describes features in prose and almost never states defaults. "not stated" below means exactly that; nothing was guessed. "Basic" = a TO can set it alone; "Support" = needs start.gg customer support; "Paid" = start.gg takes money.

## 1. Tournament level

Sources: [Getting Started](https://help.start.gg/en/articles/13766261-getting-started) · [Creating a Tournament](https://help.start.gg/en/articles/13766208-creating-a-tournament) · [Publishing](https://help.start.gg/en/articles/13764663-publishing) · [Admin Permissions](https://help.start.gg/en/articles/13766145-admin-permissions) · [Registration Caps](https://help.start.gg/en/articles/13766352-registration-caps) · [Fees](https://help.start.gg/en/articles/13768814-what-are-the-platform-fee-and-processing-fee) · [Streams and Stations](https://help.start.gg/en/articles/13766371-streams-and-stations)

| Option | Allowed values | Default | Meaning | Tier |
|---|---|---|---|---|
| Tournament name | text | required | Display name | Basic |
| Short slug | text | not stated | Short URL | Basic |
| Start / end date and time | datetime | required | When it runs | Basic |
| Time zone | the TO's zone | the TO's zone | "There is not a way to change the time zone of your tournament" | Basic (fixed) |
| Venue address | address or blank | blank | Blank for online; online vs offline is really per event | Basic |
| Primary contact | email / Discord / … | **mandatory** | Shown on the page | Basic |
| Image and banner | images | none | Branding | Basic |
| Rules | markdown | empty | Tournament rules; event rules and match rules exist too (§2) | Basic |
| Homepage visibility | Admins Only / Public (Link Only or Discoverable) | not stated | Admins Only 404s to everyone else | Basic |
| Events visibility | Admins Only / Public; per event: brackets & seeding / just seeding / events only | not stated | Seeding can be hidden until ready | Basic |
| Registration visibility | Public (Register shown) / Admins Only (closed) | not stated | The open/close switch | Basic |
| Attendee list visibility | Public / hidden | **hidden** | Public roster | Basic |
| Registration deadlines | dates | not stated | Opens and closes | Basic |
| Overall attendee cap | number | none | Under "advanced settings" | Basic |
| Custom registration questions | fields | none | Extra sign-up questions | Basic |
| Venue / event fees | money or free | free | Entry fee | Basic to set; **Paid**: 6% platform fee + processor fees online; cash on site carries no platform fee |
| Require social connections | Twitch follow/sub, Discord join; optional or required | off | Gates sign-up | Basic |
| Streams | channel entries | none | Stations & Streams tab | Basic |
| Admin roles | Administrator, Manager, Bracket Manager, Reporter | creator = Administrator | Administrator: everything incl. payments/export. Manager: attendees, brackets, report. Bracket Manager: phases, seeding, waves, stations, report. Reporter: brackets, match dashboard, printing | Basic |
| Copy from a past tournament | yes/no | — | Template | Basic |

## 2. Event level

Sources: [Event Creation](https://help.start.gg/en/articles/13766241-event-creation) · [Event Settings](https://help.start.gg/en/articles/13766250-event-settings) · [Online Check-In](https://help.start.gg/en/articles/13766335-online-event-check-in) · [Online Round Settings](https://help.start.gg/en/articles/13766200-online-round-settings) · [Pools & Seeding](https://help.start.gg/en/articles/13764646-pools-seeding) · [Bulk Add seeding](https://help.start.gg/en/articles/13764592-importing-custom-seeding-using-the-bulk-add-feature) · [Conflicts](https://help.start.gg/en/articles/13813531-conflicts) · [Reporting](https://help.start.gg/en/articles/13766247-reporting-match-results) · [Report Set mutation](https://developer.start.gg/docs/examples/mutations/report-set)

| Option | Allowed values | Default | Meaning | Tier |
|---|---|---|---|---|
| Game | start.gg's list | required | Missing games need support | Basic (adding a game: Support) |
| Platform | list | not stated | PC/PS5/… | Basic |
| Online / offline | online / offline | required | Check-in, self-report and timers are online only | Basic |
| Entrant type | singles, teams, Free-For-All, Crew Battle, custom | not stated | Team options: team names, full team required, alternates | Basic |
| Entrant cap | number; teams by teams or by players | none | Maximum entrants | Basic |
| Cost | money | free | Offline events only in the create flow | Basic |
| Visible in registration | visible / hidden | not stated | Per-event sign-up toggle | Basic |
| Registration dates / destination | dates; which phase new sign-ups land in | the first phase | | Basic |
| Event rules / match rules | markdown | empty | Format rules / per-set rules | Basic |
| Prizing | structure | none | | Basic |
| **Check-in** | per phase; check-in timer; buffer before start | off | Online head-to-head only, and only once round timers are set; not on a phase that receives progressions; "seeding will be automatically published 24 hours prior" | Basic (online) |
| No-shows | remove and rebalance pools / DQ only, bracket intact / do nothing | not stated | Chosen when check-in finalises | Basic |
| DQ timer | minutes | **15** | Minutes after round start to check in before auto-DQ | Basic (online) |
| Verify timer | min and max minutes | **12** | Time to confirm the opponent's score before it auto-verifies | Basic (online) |
| Seeding: manual | drag/swap, within or across pools; overall vs pool view | sign-up order, unseeded at the bottom | Locks once a pool starts | Basic |
| Seeding: import | Bulk Add, pasted in seed order, 50 at a time | — | | Basic |
| Seeding: generator | skill tiers | — | "Not meant for finalized seeding" | Basic |
| Seeding: randomize | — | — | In the API (`randomize-phase-seeding`); not found in the help UI | Unverified in UI |
| Conflicts / constraints | player (same region, training partners); schedule (waves) | none | Suggests swaps | Basic |
| Best of | Best Of N or Total Games N, per round | not stated | Bo3 / Bo5 per round (online round settings) | Basic |
| Who reports | entrants self-report (online H2H) + admins; "block player reporting" on stream matches | entrants online | Offline: admins and reporters | Basic |
| Disputes | player "calls a moderator"; pinned alert; chat; TO resolves | — | | Basic (online) |
| Report form | Win / Loss / DQ / score; optional per-game character, stage, stocks | score optional | | Basic |
| Byes | automatic in elimination; Swiss "points per bye" | Swiss: not stated | | Basic |

## 3. Phases and formats

Sources: [Bracket Setup](https://help.start.gg/en/articles/13766174-bracket-setup) · [Configuration Examples](https://help.start.gg/en/articles/13766168-bracket-configuration-examples) · [Progressions](https://help.start.gg/en/articles/13813655-setting-progressions-between-phases) · [Swiss](https://help.start.gg/en/articles/13813735-swiss-on-start-gg) · [Tiebreakers](https://help.start.gg/en/articles/13813755-tiebreakers) · [Round Robin Reporting](https://help.start.gg/en/articles/13813613-round-robin-reporting) · [Ladder](https://help.start.gg/en/articles/13813676-setting-up-your-ladder) · [Support-only features](https://help.start.gg/en/articles/13766257-features-that-require-help-from-customer-support) · [BracketType enum](https://smashgg-schema.netlify.app/reference/brackettype.doc.html)

**Model.** An event has phases; each starts with one. A phase has a bracket type and a pool count; each pool is a "phase group"; the whole bracket is one pool. Progressions move the top N of each pool into a target phase.

| Option | Allowed values | Default | Meaning | Tier |
|---|---|---|---|---|
| Bracket type | Single Elim, Double Elim, Round Robin, Swiss, Custom Schedule, Matchmaking (Ladder), Elimination Rounds (FFA); API also lists EXHIBITION, RACE, CIRCUIT | not stated | Per phase | Basic for SE, DE, RR, Swiss |
| **Grand final reset (DE)** | **No help page documents a toggle.** The reset set appears only when the losers-side player wins grand finals; the API exposes it through `fullRoundText` ("Grand Final Reset") | the reset is played | | Unverified toggle |
| Pools | count | 1 | Parallel pools; waves schedule them | Basic |
| Number progressing | N per pool into a destination phase | none | e.g. top 2 of each RR pool into DE | Basic |
| Land in winners or losers | per group of progressors | winners | 1st places to winners, 2nd/3rd to losers | Basic |
| Keep / avoid previous matchups | either | not stated | Keep = carry on; avoid = reseed | Basic |
| Direct entrants | hand-picked entrants placed into a later phase | none | Top seeds skip pools | Basic |
| Move all groups to winners side | action | — | Resets losers status into the next phase | Basic |
| Swiss rounds | number | ceil(log2(players)) suggested | | Basic |
| Swiss points | per match win, per game win, per bye | not stated | | Basic |
| RR / Swiss tiebreakers | ordered: S W-L, G W-L, SR, GR, OGW, OSW, OOSW, OPT, SW, H2H, LOPS; floors/ceilings | RR: **sets, then games, then head to head** | | Basic |
| Finalize placements (RR/Swiss) | manual ordering | — | TO override | Basic |
| DE 5th-place tiebreaker | on/off | **off** | Extra set for 5th | Basic |
| Third-place match (SE) | **not found in any doc** | — | | Unknown |
| Bracket size / byes | sized to entrants; byes fill gaps | automatic | Not configurable | Basic |
| Ladder | queue; check-in ~2 min; rematch avoidance ~20; sets on deck ~3 | — | Live matchmaking | Niche |
| Amateur bracket, split-phase, waterfall | — | — | | **Support** |

## 4. Live operation

Sources: [Online Match Moderation](https://help.start.gg/en/articles/13766338-online-match-moderation) · [Assigning Stations](https://help.start.gg/en/articles/13766148-assigning-stations) · [Streams and Stations](https://help.start.gg/en/articles/13766371-streams-and-stations) · [Reporting](https://help.start.gg/en/articles/13766247-reporting-match-results) · [Stream queue query](https://developer.start.gg/docs/examples/queries/stream-queue) · [Rearranging players](https://help.start.gg/en/articles/13764666-rearranging-swapping-players-in-a-bracket)

| Capability | How start.gg does it | Tier |
|---|---|---|
| Call a match | "Mark as called"; statuses not started / called / in progress / complete | Basic |
| Start a match / timer | "Start Match" starts a timer; a TO can start early or edit a match's start time | Basic |
| Assign a station | the TV icon on a match | Basic |
| Auto-assign stations | once or continuously; "Also Call Matches" | **Swiss only** |
| Stream queue | assign a match to a stream; queue per stream | Basic |
| Block player reporting on stream | per stream | Basic |
| Notifications / waiting on | each player sees their tasks (check in, report, verify); moderator requests pinned | Basic (online) |
| Forfeit / DQ | "DQ" in quick report; automatic DQ through the timer | Basic |
| Reset a reported match | "Restart" on the Report tab | Basic |
| Reset a pool / a phase | Bracket reset (one pool) or Phase reset (all); "results cannot be recovered" | Basic |
| Reseed between phases | keep or avoid previous matchups; Edit Mode | Basic |
| Drop an entrant | remove, or DQ | Basic |
| Public page | Overview, Bracket, Standings, Stats; upcoming matches; pools by seed or A–Z | Basic |
| Print brackets | yes | Basic |

## 5. Standings and results

Sources: [Tiebreakers](https://help.start.gg/en/articles/13813755-tiebreakers) · [Round Robin Reporting](https://help.start.gg/en/articles/13813613-round-robin-reporting) · [Leagues & Circuits](https://help.start.gg/en/articles/13766319-leagues-circuits-on-start-gg) · [Set object](https://smashgg-schema.netlify.app/reference/set.doc.html)

| Item | start.gg behaviour | Tier |
|---|---|---|
| SE/DE placement | each set carries `wPlacement`/`lPlacement`; losers in the same round tie. DE: 1, 2, 3, 4, 5, 5, 7, 7, 9×4, 13×4, 17×8 … (standard convention; no doc spells it out) | Basic |
| 5th-place tie in DE | optional extra set | Basic |
| RR / Swiss standings | points + ordered tiebreakers; "Finalize Placements" override | Basic |
| Points across a series | Leagues/Circuits — "requires contacting start.gg's support team first" | **Support** |
| Exports | attendee export (Administrator only); phase seeding CSV | Basic |

## 6. Not basic on start.gg — do not copy as a basic

- Leagues and circuits (series points): support approval.
- Amateur brackets, split-phase, waterfall, changing an event's ruleset: support only.
- Online payments: 6% platform fee (since 2025-02-14) plus processor fees.
- Auto-assigning stations: Swiss only.
- Check-in, self-reporting, DQ and verify timers: online head-to-head only.
- Niche: Fantasy, shops, LoL tournament codes, ladder matchmaking, Twitch sub-only events, location-restricted registration, discount codes.

## API shape, for the later mirror

- GraphQL, POST to `https://api.start.gg/gql/alpha`, header `Authorization: Bearer <token>` (a personal token from developer settings) — [sending requests](https://developer.start.gg/docs/sending-requests), [authentication](https://developer.start.gg/docs/authentication).
- A tournament by `slug` (`tournament/<name>`); an event by `id` or slug `tournament/<t>/event/<e>` (slug form not confirmed in the docs opened); phases, phase groups and sets by numeric `id`. A set has `round` (negative = losers bracket), `fullRoundText`, `identifier`, `slots[].entrant`, `winnerId`, `games[]`, `station`, `stream`. Results go back through `reportBracketSet` — [sets in event](https://developer.start.gg/docs/examples/queries/sets-in-event), [report set](https://developer.start.gg/docs/examples/mutations/report-set).
- Rate limit: 80 requests per 60 seconds, at most 1000 objects per request including nested — [rate limits](https://developer.start.gg/docs/rate-limits).

## Could not find, or sources disagree

- A grand-final reset toggle: no article documents one; a search summary mentioned "2 Games" vs "1 Game" grand finals but could not be traced to a start.gg page. TO rulesets on start.gg routinely say "Grand Finals Bo5 with bracket reset".
- A third-place match in single elimination: not mentioned anywhere read.
- Defaults are mostly not stated; exceptions: DQ timer 15, verify timer 12, one phase per event, hidden attendee list, the RR tiebreaker order.
- Random seeding / seeding by rating: an API mutation exists for random; nothing on rating beyond the generator's skill tiers.
- Best-of per round is documented only for online events.
- DE placement numbers are inferred from convention and the API's placement fields.
- blog.start.gg returned 403; "Running Your Head-to-Head Event" is an index only.

## The researcher's recommendation for a first build (an input, not a decision)

One event per tournament, singles only: name, game, start time, entrant cap, sign-up open/close, rules text. Optional check-in window; no-shows removed before the bracket is made. Seeding by hand on the site plus randomise. Single and double elimination only, byes automatic, grand-final reset a setting. Best of N with one override from top 8. Either player reports, the opponent confirms, staff override at any time; DQ; reset a match and what follows it. Live page: bracket, called matches, standings with tied placements. Later: pools/phases, round robin, Swiss, stations, streams, ladders, teams, fees, series points.
