# Marathon orgs research — Fast Paced Events, Fastest Furs, Lady Arcaders (where their schedules live, what reads them)

> **Audience:** the owner and future sessions deciding which marathon feeds to add next. **Status:** TRACKED ·
> research only, nothing built. **Last verified: 2026-09-26 ~12:2x Phoenix** — every fact below was read live that
> day (one GET each, `urllib` with a plain User-Agent, from the build machine, not from Fly). **NOT checked:** the
> bot's own `ScheduleClient` (aiohttp) against any of these hosts, or from Fly (KI-30's datacenter wall is untested on
> horaro.net for these slugs, `cheetah.fastestfurs.com` and `ladyarcaders.com`); the orgs' Discord servers (Lady
> Arcaders says its Discord carries the freshest event news); rate limits; Twitch channel pages themselves (the logins
> come from each org's own links and its schedule records, not from twitch.tv). `docs/info/README.md` was not given an
> index line (brief: one new file only). Secret NAMES only — there are none here.

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
