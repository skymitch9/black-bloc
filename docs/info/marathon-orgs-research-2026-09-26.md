# Marathon orgs research — Fast Paced Events, Fastest Furs, Lady Arcaders (where their schedules live, what reads them)

> **Audience:** the owner and future sessions deciding which marathon feeds to add next. **Status:** TRACKED ·
> research only, nothing built. **Last verified: 2026-09-26 ~12:2x Phoenix** — every fact below was read live that
> day (one GET each, `urllib` with a plain User-Agent, from the build machine, not from Fly). **NOT checked:** the
> bot's own `ScheduleClient` (aiohttp) against any of these hosts, or from Fly (KI-30's datacenter wall is untested on
> horaro.net for these slugs, `cheetah.fastestfurs.com` and `ladyarcaders.com`); the orgs' Discord servers (Lady
> Arcaders says its Discord carries the freshest event news); rate limits; Twitch channel pages themselves (the logins
> come from each org's own links and its schedule records, not from twitch.tv). `docs/info/README.md` was not given an
> index line (brief: one new file only). Secret NAMES only — there are none here.
> **RGL section added 2026-09-26 ~13:00 Phoenix** (same method, plus Bluesky's public API and the live bot's
> `/api/golive/spotlight`). **NOT checked for RGL:** X/Twitter timelines (X shows only a pinned post without a login;
> no nitter mirror answered), the Discord server (its invite API answered 404), the Twitch schedule page (script-rendered),
> Tiltify (no campaign found by search), rgltv.com's scripts for a list endpoint, and whether `n6430th` reads through the
> bot's own client on Fly.

## The ask, verbatim (owner, 2026-09-26 11:4x)

*"Look into Fast Pace Events, Fastest Fur, Lady Arcaders for marathon schedules and channels"*

⚠️ The names are **Fast Paced Events** (FPE; the events are titled *Fast Pace for …*) and **(Team) Fastest Furs**.

## The table

| Org | Twitch login | Bot row | Schedule host | Latest schedule URL | Last two events | Next event | Coverage verdict |
|---|---|---|---|---|---|---|---|
| **Fast Paced Events** | `fastpacedevents` | **no row** | **horaro.net**, a NEW event slug per marathon (Oengus for 2021–2023) | https://horaro.net/fpff3/schedule | Fast Pace for Friendspace 3, 2026-08-22 · Fast Pace for Pride 2025, 2025-11-28 | none announced (not found) | **covered by hand** (staff paste the horaro link; the reader parses it); a horaro FEED on a fixed slug would **not** find the next event → a new *horaro-by-channel* feed to discover them |
| **Fastest Furs** | `fastestfurs` | **no row** | **own site + JSON API** `cheetah.fastestfurs.com` since 2026 (horaro.net 2020–2025) | https://fastestfurs.com/schedule/21 (page, inferred from the site's route) · API https://cheetah.fastestfurs.com/api/public/schedules/event/21 | FWA 2026 (in person), 2026-05-08–10 · FWA ONLINE 2026, 2026-04-18–19 | **Fall Fest 2026, 2026-10-08 → 10-11** (schedule published, 55 runs) | **needs a new reader**: a `fastestfurs` source (events list + public schedule JSON) |
| **Lady Arcaders** | `ladyarcaders` | **no row** | **own site** `ladyarcaders.com/events/<n>/schedule/` with an **ICS feed** per event (horaro.net 2023–2024, Oengus 2022) | https://ladyarcaders.com/events/24/schedule/ (ICS: `…/events/24/schedule/calendar/`) | Super Showcase 2026, 2026-09-03–06 · Out of Bounds Torontrois (in person, Toronto), 2026-06-14–15 | none announced (events page: only the year-round *Attract Mode!*) | **needs a new reader**: an ICS reader for `ladyarcaders.com`, and discovery by probing the next event number |

Bot rows, read 2026-09-26 12:1x via `scripts/read.ps1 -Path /api/golive/spotlight`: the live Go-live list has five
channel rows — `esamarathon` (4), `gamesdonequick` (3), `rpglimitbreak` (5), `speedstuff4charity` (6),
`retrogaminglivetv` (7). None of the three orgs has a row, so **nothing can be fed yet** (a feed needs a channel row —
`marathon-feeds-design.md`, *The ask*).

## Fast Paced Events

**Who:** a speedrun events team founded January 2022 by Amber Cyprian, raising money for LGBTQ+ and mental-health
charities (*Fast Pace for Pride / Headspace / Friendspace*). Twitch **`fastpacedevents`**; YouTube
`https://www.youtube.com/channel/UCozhMzfNhd8oJmaQuGHFUiQ` (VODs). `fastpacedevents.com` redirects to
`https://linktr.ee/FastPacedEvents`, which links the current schedule and nothing else schedule-shaped.

**Evidence:**
- Linktree: *Fast Pace for Friendspace 3 Schedule* → `https://horaro.net/fpff3/schedule`; Twitch
  `https://www.twitch.tv/fastpacedevents`.
- `GET https://horaro.net/-/api/v1/events/fpff3/schedules` → 200, one schedule `schedule`, *Fast Pace for Friendspace
  3*, start `2026-08-22T10:00:00-04:00`, `twitch: fastpacedevents`, 12 items.
- `GET https://horaro.net/-/api/v1/events?name=fast&max=100` (horaro's event search) lists FPE's events, one slug
  each: `fpfp2022`, `fpfp2023`, `fpfh`, `fpfh2023`, `fpff` (2024-08-18), `fpffs2` (2025-01-18), `fpfp2025`
  (2025-11-28, 41 items, `https://horaro.net/fpfp2025/schedule`), `fpff3` (2026-08-22). The `twitch` field is
  `fastpacedevents` / `FastPacedEvents` on all of them except `fpfh` (`tgh_sr`, 2021).
- Earlier events were on Oengus: `GET https://oengus.io/api/v1/marathons/FPFH2023` → `twitch: FastPacedEvents`
  (capital letters), 2023-12-01 → 12-04. Today's Oengus `for-home` (read 12:1x, 31 marathons) holds no FPE marathon.
- `fpff3/schedule.json` columns: `⠀`, `⠀`, **`Runner`**, **`Game`**, `Category`, `Platform`, `Host` —
  `parse_horaro` finds Game / Runner / Category by name, so the existing reader parses it. Runners are plain names
  (`Ryan Ford`), no Twitch links, so matching is by name only (the ESA case).

**Verdict:** **covered by hand; a feed needs a small new mode.** Staff can paste `https://horaro.net/<slug>/schedule`
today (the horaro reader is built). But the existing horaro FEED watches ONE event slug (`feed_ref = esa`) and lists
its schedules — right for ESA, which keeps one event with many schedules, wrong for FPE, which makes a **new event
per marathon**. A feed on `fpff3` would never see `fpfp2026`.

**Odd:** the brand is *Fast Paced Events*, the events *Fast Pace for …*; `fastpacedevents.com` is just the Linktree.
No 2026 Pride/Headspace event was found (web search and horaro search) — **inferred** that none is announced yet.

## Fastest Furs

**Who:** Team Fastest Furs, a furry speedrunning group (since 2019) running a spring event (now *LIVE at FWA*, the
Furry Weekend Atlanta convention, plus an online lead-in) and a fall *Fall Fest*, mostly for Trans Lifeline and
Lost-n-Found Youth. Twitch **`fastestfurs`**; YouTube `https://www.youtube.com/c/TeamFastestFurs/` (both links read
from the site's bundle `https://fastestfurs.com/assets/index-B9QM-1JL.js`).

**Evidence:**
- `https://fastestfurs.com/` (a React app): title *Fall Fest 2026 — Fastest Furs*, `og:description` *Sign ups are
  closed — October 8-11 2026*. The bundle names the API base `https://cheetah.fastestfurs.com` and the routes
  `/api/events`, `/api/public/schedules/event/${id}`, and a page route `/schedule/$eventId`.
- `GET https://cheetah.fastestfurs.com/api/events` → 200, a JSON list of 17 events, each `{id, name, short,
  startDate, endDate, amountRaised, charityName, submissionsOpen, isInPerson, playlistLink, …}`, newest first:
  **21** *Fastest Furs Fall Fest 2026* (`FFFF26`, 2026-10-08 → 10-11), **19** *LIVE at FWA 2026* (2026-05-08 → 05-10,
  in person), **18** *ONLINE for FWA 2026* (2026-04-18 → 04-19), **16** *Fall Fest 2025* (2025-10-09), 15 FWA 2025, … 1
  *Fastest Furs For Life* (2019). No `twitch` field (single-org API, so none is needed).
- `GET https://cheetah.fastestfurs.com/api/public/schedules/event/21` → 200, `{id, eventId, startDateTime
  2026-10-08T14:00:00Z, timeZone, scheduleItems[]}` — 65 items (55 `run`, 10 `break`), each `{itemType, duration`
  (minutes)`, setupTime, orderIndex, label, runs: {name` (game)`, category, console, estimatedTime, runners` (a plain
  name string, e.g. `bouzny`)`, pronouns, status}, scheduleItemHosts: [{host: {name}}]}`. Event 19's schedule answers
  the same shape (27 KB).
- horaro.net (`?name=fur` search) holds their 2020–2025 events (`ffff2020` … `fallfest2025`
  `https://horaro.net/fallfest2025/schedule`, `fwa2025`); **nothing for 2026** — they moved to their own site.

**Verdict:** **needs a new reader** — a `fastestfurs` source. The page URL `https://fastestfurs.com/schedule/21` is
**inferred** from the route (the app is script-rendered; not opened in a browser).

**Odd:** the move off horaro.net happened between Fall Fest 2025 and FWA 2026. `startDate`/`endDate` on older events
are the same day (only the newest two carry a real end). Runners are names, not logins.

## Lady Arcaders

**Who:** a women and femme gaming collective (since 2022) running the annual *Super Showcase* (LASS, for CARE), the
in-person *Out of Bounds* in Toronto, one-day events (*Microthon*, *Galloping for the Gals*), a yearly *Raid Train*,
and the rolling *Attract Mode!* series. Twitch **`ladyarcaders`**; YouTube `https://www.youtube.com/@ladyarcaders`.

**Evidence:**
- Event pages link their schedules by number: `/event/lass-2025/` → `/events/18/schedule/` (2025-08-21 → 24);
  `/event/microthon/` → `/events/21/` (2026-04-04); `/event/laoob3/` → `/events/22/` (2026-06-14 → 15);
  `/event/galloping-for-the-gals/` → `/events/23/` (2026-03-22); **`/event/lass-2026/` → `/events/24/schedule/`**
  (2026-09-03 → 06, *on twitch.tv/ladyarcaders*).
- Every schedule page offers a **CALENDAR FEED**: `GET https://ladyarcaders.com/events/24/schedule/calendar/` → 200,
  `text/calendar`, `X-WR-CALNAME: Lady Arcaders Super Showcase 2026 Schedule`, 47 `VEVENT`s, first 2026-09-03 12:05,
  last 2026-09-06 21:43 America/Toronto; each `SUMMARY: [LASS2026] <title> (<performer>)`, `DESCRIPTION: … by
  <performer>  Time Estimate: 00:10:00`, `LOCATION: https://ladyarcaders.com/event/lass-2026/`, a stable `UID`.
  `/events/22/schedule/calendar/` answers the same (`[laoob3]`).
- `GET https://ladyarcaders.com/events/25/schedule/calendar/` → **200 with an empty body** — no event 25 yet (or an
  unpublished one; which of the two is **not known**).
- `/events/`: *"The most up to date information about our upcoming events can be found on our Public Discord
  server"*; Upcoming lists only *Attract Mode! — All Year Round* (*"There are no upcoming showcases!"*).
- History: horaro.net `lass-2023`, `lass-2024` (`https://horaro.net/lass-2024/schedule`), `laoobt-2024`,
  `la-raid-train-2024`; Oengus `GET https://oengus.io/api/v1/marathons/lass-2022` → `twitch: ladyarcaders`
  (`scheduleDone: false`). A horaro event `2ronto` (*Lado Arcaders 2ronto*, 2025-08-16, no `twitch`) looks like their
  2025 Out of Bounds (**inferred**; the site's own page is `/event/laoob2/`).

**Verdict:** **needs a new reader** — an ICS reader for `ladyarcaders.com/events/<n>/schedule/calendar/`.

**Odd:** many of their events are showcases, not speedruns (art, music, first playthroughs); the ICS carries
performers as display names, not logins. `fastandfabs` restreams some of their events in French on horaro.net
(`lass2024fr`, `laoobt2024fr`) — not theirs.

## What it would take (smallest next step per org)

All three first need a **channel row on the Go-live page** (staff: Streamers ▸ add channel `fastpacedevents` /
`fastestfurs` / `ladyarcaders`, marathons on). That alone gives go-live posts and lets staff paste a schedule by hand
where a reader exists.

1. **Fast Paced Events — cheapest.** Row `fastpacedevents`, then paste `https://horaro.net/<slug>/schedule` per
   marathon (works today). For automatic discovery, extend the horaro feed with a **by-channel mode**: read
   `https://horaro.net/-/api/v1/events?name=<words>` (or page through `/-/api/v1/events`) and keep events whose `twitch`
   equals the row's login case-insensitively — the Oengus-feed pattern (filter by `twitch`) on horaro's event list.
   ⚠️ Not verified: whether `/-/api/v1/events` pages the whole site without `name` and how many pages that is; a name
   filter (`fast pace`) is the cheap version but misses a renamed event. A horaro feed on slug `fpff3` would add
   nothing new.
2. **Fastest Furs — a new source, small.** Row `fastestfurs` + a `fastestfurs` reader: feed = `GET
   cheetah.fastestfurs.com/api/events` (new ids ahead of now), runs = `/api/public/schedules/event/<id>` (start at
   `startDateTime`, walk items by `orderIndex`, each run lasts `duration` + `setupTime` minutes, `runners` split like
   horaro players, hosts from `scheduleItemHosts`). `read_url` learns `fastestfurs.com/schedule/<id>`. Worth doing
   before 2026-10-08 if the owner wants Fall Fest 2026 on the board.
3. **Lady Arcaders — a new source, medium.** Row `ladyarcaders` + an ICS reader for
   `ladyarcaders.com/events/<n>/schedule/calendar/` (`DTSTART`/`DTEND` with `TZID`, `SUMMARY` `[SHORT] title
   (performer)`, `UID` as the external id). Discovery has no list endpoint: a feed would probe `<last n>+1` each
   poll and treat a non-empty calendar as a new event (event 25 answered 200-empty today). Their Discord is the
   announced source of truth, so a staff-pasted link may be the honest first step.

## Retro Gaming Live (added 2026-09-26)

**The ask, verbatim (owner, 2026-09-26 12:5x Phoenix):** *"for retro gaming do more research, can we check twitter or
other sources to glimpse how they might have scheduled in the past"*

⚠️ **This corrects `marathon-feeds-design.md`'s "RGL has no source".** RGL has published **every marathon since 2016 on
horaro.net** — about 60 events under the horaro account **`RGLtvMarathons`**. The 2026-09-25 check missed them because
horaro's search matches event NAMES, and the names say **RGL / RGLtv**, never *Retro Gaming Live* (measured today:
`?name=Retro%20Gaming` → 0 results; `?name=RGL` → 49, 46 of them RGL's). `retrogaminglive.tv` really does not resolve;
the live site is **`rgltv.com`**.

| Org | Twitch login | Bot row | Schedule host | Latest schedule URL | Last two events | Next event | Coverage verdict |
|---|---|---|---|---|---|---|---|
| **Retro Gaming Live (RGLtv)** | `retrogaminglivetv` | **row 7** (marathons on; live now, title *N64 30th Anniversary Marathon! … !schedule*) | **horaro.net**, a NEW event slug per marathon, owner `RGLtvMarathons` (since 2016; some older ones also on horaro.org); sign-ups on **rgltv.com** | https://horaro.net/n6430th/schedule | N64 30th Anniversary Marathon, 2026-09-25 → 09-29 (live) · SHMUPtember 2026, 2026-09-19 → 09-20 | **A Fistful of Brawlers, 2026-10-17 → 10-20**; then **Halloween Horror 2026, 2026-10-30 → 11-02** (sign-ups only; no horaro schedule yet) | **covered by hand** (staff paste the horaro link; the reader parses it); a `horaro_events` feed named **`RGL`** finds about **half** of their 2026 events — full discovery needs a different match (below) |

**Who:** RGLtv (*RetroGamingLiveTV*), "a collaboration of streamers" launched 2015-10-03, running retro marathons,
multi-game races (NEScathlon, Tiny Ten), weekly shows (WADSday, Retro Raffles) and 1–3 marathons a month in 2026.
Places, each tried today:
- Twitch **`retrogaminglivetv`** (https://www.twitch.tv/retrogaminglivetv; the schedule page is script-rendered, not read).
- YouTube `https://www.youtube.com/channel/UCMh3qoCHzG-L1gRZosR0Jyw` (from the Bluesky bio; `@RetroGamingLiveTV`).
- X/Twitter **`@retrogaminglive`** (https://x.com/retrogaminglive — 4,813 posts; the logged-out page shows the bio and
  one pinned post of 2025-02-21; the timeline needs a login, **not read**). horaro events up to 2025 name
  `twitter: retrogaminglive`.
- Bluesky **`rgltv.bsky.social`** (since 2023-09-03; readable without login through `public.api.bsky.app`). The 2026
  horaro events name `bluesky: rgltv.bsky.social` and drop the twitter field, so **Bluesky has replaced X as their
  announcement feed** (inferred from those fields and the post volume, not stated by them).
- Discord `https://discord.gg/c4UWZqWT64` (Bluesky bio). `discord.com/api/v10/invites/c4UWZqWT64` → **404**, so the
  invite may be expired (not joined).
- Website **`https://rgltv.com/`** — a Next.js app titled *RGLtv streaming tools*; it hosts **submission forms**
  `rgltv.com/events/<slug>/submission`. `/events`, `/events/N6430th`, `/events/N6430th/schedule`, `/schedule` and
  `/api/events` → 404. Older sites: `retrothon.net` (does not resolve today; Wayback
  `http://web.archive.org/web/20230602052946/http://retrothon.net/` shows *Retrothon 2020 … The schedule is here*,
  linking `retrothon.net/schedule/`, 74 captures 2018–2023) and `www.rgltv.eu` (connection refused; named as the
  website on 2019–2020 horaro events). No Wayback snapshot of `rgltv.com`, `retrogaminglive.tv` or
  `twitter.com/retrogaminglive`.
- Oengus: nothing of theirs (today's `for-home`, 31 marathons; *Retro Runway Restage Raid Relay* `RRRRR` is a Japanese
  event, not RGL; no `site:oengus.io` hit). speedrun.com: a news post *Celebrate 30 Years of N64 w/ the 30th
  Anniversary Marathon!* (`https://www.speedrun.com/news/17vrmj5x-celebrate-30-years-of-n64-w-the-30th-anniversary-marathon`,
  403 to a script; seen through search only). Tiltify: no campaign found by search.

**How they scheduled past events** — every one a horaro.net event with one schedule, `twitch: retrogaminglivetv` at
schedule level, timezone America/New_York; each announced on Bluesky with the horaro link about **2–3 weeks ahead**
(`n6430th` "schedule is out" 2026-09-05 for 09-25; `shmup26` linked 2026-09-05 for 09-19):

| Event | Start (ET) | Schedule URL | Items |
|---|---|---|---|
| N64 30th Anniversary Marathon | 2026-09-25 10:00 (last item 09-29 03:12) | https://horaro.net/n6430th/schedule | 67 |
| SHMUPtember 2026 | 2026-09-19 13:00 (last item 09-20 20:46) | https://horaro.net/shmup26/schedule | 22 |
| NINJULYDEN 2026 | 2026-07-25 11:00 | https://horaro.net/ninja26/schedule | not counted |
| RPGLtv Gauntlet: The Quest for Good RNG | 2026-06-25 12:00 | https://horaro.net/rpgltvgauntlet/schedule | not counted |
| MEGAmorial Day Weekend '26 | 2026-05-23 13:00 | https://horaro.net/megamorial26/megaschedule | not counted |
| The Kessel Run X (Star Wars) | 2026-05-01 13:00 | https://horaro.net/tkr26/swschedule | 28 |
| Retrothon 2026 | 2026-04-18 12:00 (last item 04-26 23:59) | https://horaro.net/retrothon26/schedule | 199 |
| RGLtv Do The MAR10 26 | 2026-03-07 15:00 | https://horaro.net/rgldothemar10/rglmar10 | 30 |
| RGLove 2026 | 2026-02-12 12:00 | https://horaro.net/rglove26/rglove26 | 91 |
| RGLtv's JANKuary 2026 | 2026-01-17 13:00 | https://horaro.net/jank26/schedule | 41 |
| Coin-op Classic 2025 · 10 Year Anniversary · Halloween Horror 2025 | 2025-12-13 · 11-13 · 10-24 | `coc25` · `rgltv10` · `hh2025` (`/schedule`) | 36 · 21 · 46 |

Older (all still answer): Retrothon 2019–2025 (`retrothon2019` … `retrothon2025`), RGLove 2018–2025, Halloween Horror
2019–2024, Feed the Kids 2019–2023, Secret Santa 2018–2024, Kessel Run 2025, PS 25th (`psx25`), Turbofest 2021, the
first ones in 2016 (`metroidmaraton`, `rglminimarathon`). Some older schedules were also served at horaro.org (a search
hit: `https://horaro.org/retrothon2023/schedule?key=shhhh`, not opened).

**Evidence per source:**
- **horaro.net** — `GET https://horaro.net/-/api/v1/events?name=RGL&max=100` → 49 events, 46 with `twitch:
  retrogaminglivetv`; searches for `Retro`, `Retrothon`, `Kessel`, `N64`, `Turbo` and the slugs in Bluesky posts fill in
  the rest; every `/-/api/v1/events/<slug>/schedules` answered 200. `n6430th/schedule.json` columns `Runner, Game,
  Category, Layout, webcam, Aspect, Screens, Theme, OG Start Time` (shmup26, retrothon26, rgldothemar10 alike) —
  `parse_horaro` finds Game / Runner / Category by name, so **the existing reader parses it** (read by column name,
  not run through the bot's code). Runners are plain names (`ryanford`, `tuerkenheimer`), no Twitch links — match by
  name (the ESA / FPE case).
- **Bluesky** — `GET https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor=rgltv.bsky.social&limit=100`
  (100 posts, back to 2026-05-09): every marathon post links `horaro.net/<slug>/schedule` (ninja26, rpgltvgauntlet,
  megamorial26, shmup26, n6430th) or `rgltv.com/events/<slug>/submission` (rpggauntlet26, ninjulyden26, shmup26,
  N6430th, hh2026, brawl26). No schedule was posted as an image only.
- **X/Twitter** — logged-out page: bio + one pinned post. Web search summarises older tweets linking
  `horaro.org/retrothon2019/schedule` (search-engine text, **not opened**). No nitter mirror answered (`nitter.net`
  refused).
- **rgltv.com submission pages** (read today): *Halloween Horror 2026* — "Submissions will be open until September 27th
  and the marathon will run October 30th – Nov 1st", *Planned event dates: Fri Oct 30 2026 – Mon Nov 02 2026*; *A
  Fistful of Brawlers* — "open until September 27th … October 17th – 20th", *Planned event dates: Sat Oct 17 2026 – Tue
  Oct 20 2026*. Neither has a horaro event yet (`brawl26`, `hh2026`, `hh26`, `fistful26` → 404 on horaro; the real
  slugs are **unknown** until published).

**Verdict:** **covered by hand today; a feed finds about half.** Staff can paste `https://horaro.net/n6430th/schedule`
now (row 7 exists, marathons on). The new `horaro_events` feed (search by feed NAME, then keep events whose EVENT-level
`twitch` is the login) was measured against RGL's ten 2026 events: name **`RGL`** lists and matches `jank26`,
`rglove26`, `rgldothemar10`, `shmup26`, `n6430th` (5 of 10) and **misses** `retrothon26` (name lacks RGL AND its
event-level `twitch` is **null** — only its schedule says `retrogaminglivetv`), `tkr26`, `megamorial26`,
`rpgltvgauntlet`, `ninja26` (names lack RGL; `RPGLtv` does not contain `RGL`). So an `RGL` feed would miss their
biggest event (Retrothon). Not unreadable: nothing found lives only in images or Discord.

**What it would take:** (1) **now, no build:** staff paste the horaro link per marathon on row 7. (2) **cheap, no
code:** a `horaro_events` feed on row 7 named `RGL` (Add a feed ▸ horaro.net events) — about half. (3) **full
discovery, small build:** match on horaro **`owner` = `RGLtvMarathons`** (present on every event in the list payload)
or on the SCHEDULE's `twitch`, and allow several search words (`RGL`, `Retrothon`, `Kessel`, …) — ⚠️ still misses a
new event whose name shares no word; a whole-site walk (3,600+ events, ~37 pages) is the only complete version and was
rejected for FPE as too heavy. (4) **earlier notice, not recommended yet:** the `rgltv.com/events/<slug>/submission`
pages carry planned dates weeks before a schedule exists, but no list endpoint was found — the slugs appear only in
Bluesky posts, so it would mean a Bluesky-post reader.
