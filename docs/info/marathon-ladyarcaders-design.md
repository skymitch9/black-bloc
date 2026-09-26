# Lady Arcaders — a fifth marathon source, found by probing ladyarcaders.com's next event numbers

> **Audience:** the conductor, reviewers and future sessions touching marathon sources. **Status:** TRACKED ·
> 🔨 **BUILT on branch `marathon-ladyarcaders`** (off `main` `a3ac5132`; commits `f450ee59` code + tests + fixtures,
> `8d0d4400` site + mock, and the docs commit) — **NOT merged, NOT deployed, nothing has met Discord or Fly.**
> **No schema change** (`SCHEMA_VERSION` stays **68**; the feed's memory reuses `marathon_feeds.seen`), registry keys
> unchanged in number (two defaults / help texts reworded). **Last verified: 2026-09-26 ~12:4x Phoenix** — six live
> GETs from the build machine (`urllib`, plain User-Agent, one read per URL), listed under *The live shapes*.
> **NOT checked:** the bot's own `ScheduleClient` (aiohttp, `BROWSER_AGENT`) against ladyarcaders.com, or anything from
> Fly (KI-30's datacenter wall is untested on this host); what an event that EXISTS but has not published a schedule
> answers (no such event was found live); rate limits; the live channel list (no `ladyarcaders` row exists today, per
> the research doc's 12:1x read). Secret NAMES only — there are none here.

## The ask, verbatim

Owner, 2026-09-26 11:4x Phoenix: *"Look into Fast Pace Events, Fastest Fur, Lady Arcaders for marathon schedules and
channels"* — answered by [`marathon-orgs-research-2026-09-26.md`](marathon-orgs-research-2026-09-26.md) — then, 12:3x:
*"Build them all now"*. This doc is the Lady Arcaders third; Fastest Furs and the horaro-by-channel mode are sibling
branches (`marathon-fastestfurs`, `marathon-horaro-events`) built in parallel on the same shared files.

## The live shapes (2026-09-26 ~12:4x Phoenix)

| GET | Answer |
|---|---|
| `https://ladyarcaders.com/events/24/calendar/` | ⚠️ **404** (`text/html`, 315 B) — the brief's form is not the calendar |
| `https://ladyarcaders.com/events/24/schedule/calendar/` | **200**, `text/calendar; charset=utf-8`, 24,481 B, **CRLF** line ends, no folded lines (longest 129 chars — longer than RFC 5545's 75, unfolded) |
| `https://ladyarcaders.com/events/24/schedule/` | **200**, `text/html`, 127 KB, server-rendered (jQuery + moment, no JSON endpoint, no `wp-json`, no `ld+json`); links the calendar as `/events/24/schedule/calendar/` |
| `https://ladyarcaders.com/events/25/calendar/` | **404** |
| `https://ladyarcaders.com/events/25/schedule/calendar/` | ⚠️ **200 with an EMPTY body** (`text/html`, 0 B) — the research's reading held |
| `https://ladyarcaders.com/events/25/schedule/` | **redirect → `/opportunities/`** (200, *Opportunities · Lady Arcaders*) |

**The calendar (event 24):** `VCALENDAR` with `PRODID:-//Lady Arcaders//NONSGML//EN`, **`X-WR-CALNAME:Lady Arcaders
Super Showcase 2026 Schedule`**, `X-WR-TIMEZONE:America/Toronto`, no `VTIMEZONE` block; **47 `VEVENT`s**, each with:

| Property | Shape (real example) |
|---|---|
| `UID` | a bare number, stable per run (`1116`) |
| `DTSTART` / `DTEND` | **`;TZID=America/Toronto:20260903T121500`** — local time with a zone id, never `Z`, never date-only |
| `SUMMARY` | `[LASS2026] SAROS (Nimelya)` — `[SHORT] <game> (<performers>)`; several performers joined by an escaped comma: `BirdGut (mechamomo\, sapphire_in_pink)` |
| `DESCRIPTION` | `SAROS (NG+ All Bosses (Modifiers)) by Nimelya   Time Estimate: 00:47:00` — `<game> (<category>) by <performers>` + three spaces + the estimate; the category can hold nested parentheses |
| `LOCATION` | the event page, `https://ladyarcaders.com/event/lass-2026/` (the slug page, which carries no number) |
| also | `DTSTAMP`, `CREATED`, `LAST-MODIFIED` (all `TZID`), `SEQUENCE:0`, `STATUS:CONFIRMED`, `TRANSP:OPAQUE` |

The org's own segments (*Welcome to LASS 2026!*, *Day 2 Begins!*, *The End!*) name **`Lady Arcaders`** as the
performer and `Super Showcase 2026` as the category. Stray spaces occur (`Adventures with Barbie: Ocean Discovery
(Any% )`). ⚠️ **The calendar carries NO hosts or commentators** — the HTML page does (`<span class="badge bg-success"
title="Host">`, `title="Commentator"`, with pronouns and platform), see Deviation 2.

**The page is not cleaner than the ICS**: server-rendered table rows, no JSON behind it. The ICS is the reader.

## The design, as built

**Source** `LADYARCADERS = "ladyarcaders"` (`marathon_sources.SOURCES`, last). `read_url` accepts
`https://[www.]ladyarcaders.com/events/<n>` with nothing, `/schedule`, `/schedule/calendar` or `/calendar` after it
(trailing slash, query and fragment optional) → `("ladyarcaders", "<n>")`, the number without leading zeros.
`schedule_page` → `https://ladyarcaders.com/events/<n>/schedule/`; `site_of` → `ladyarcaders.com`; `SOURCE_WORDS` →
*Lady Arcaders*. The event pages by slug (`/event/lass-2026/`) carry no number and are not read.

**Reader** — `black_bloc/marathon_ladyarcaders.py` (pure functions, stdlib only; `zoneinfo` via `timezones.zone`):

- `parse_ics(text)` → every `VEVENT` as `{PROPERTY: text}`: CRLF / LF / CR, a line starting with a space or tab
  continues the last (unfolding), `\,` `\;` `\\` `\n` `\N` unescaped, parameters parsed (quoted values allowed), a
  nested component (`VALARM`) does not overwrite its event. `DTSTART` / `DTEND` become UTC ISO strings: `TZID`, `Z`,
  floating (the calendar's `X-WR-TIMEZONE`, else UTC), date-only (`VALUE=DATE` or 8 digits → midnight UTC); an unknown
  `TZID` falls back like a floating time; junk → `None`.
- `parse_ladyarcaders(events)` → one `Run` per VEVENT in start order: **game** = `SUMMARY` minus the `[SHORT]` tag and
  the LAST balanced parenthesis group (the performers); **category** = `DESCRIPTION` minus `Time Estimate: …`, minus
  `" by <performers>"`, then the last balanced group when what precedes it is the game (nested parentheses kept,
  whitespace collapsed); **people** = the performers split on `,`, each `Person(name, None, "runner")`, the org's own
  name (`ORG_NAMES`) dropped; **run_seconds** = the `Time Estimate`, else `DTEND − DTSTART`; `external_id` = `UID`
  (else `#<index>`); `order` = place in time order. No Twitch logins (the calendar has none).
- `calendar_runs` / `calendar_resolve` — reached from `ScheduleClient.runs` / `.resolve` (a local import: the module
  imports `marathon_sources`). A 404 is *ladyarcaders.com has no event N*; any other non-200 *answered N*; a
  non-calendar body *answered with something that is not a schedule*; **no VEVENT → `ScheduleError(unpublished=True)`**
  (*ladyarcaders.com has no schedule published for event N yet*) — the GDQ-404 / Oengus path, so runs are kept and
  nothing counts as a failure. `resolve` refuses an empty calendar in the same words (not `unpublished`); the name is
  `X-WR-CALNAME` minus a trailing ` Schedule`, else the `[SHORT]` tag, else *Lady Arcaders event N*.
- `ScheduleClient` gained `text(url)` (and an injectable `text_request`), on the SAME aiohttp session as `_json`
  (`_open()`), same agent, same timeout, transport errors wrapped (checklist 7).

**Feed** `LADYARCADERS_FEED = "ladyarcaders"` (`marathon_feeds.FEED_SOURCES`, last); `feed_ref` = the channel's login
(as Oengus — `create_feed` and **Move to channel…** set it). Each check (`cogs/content/marathon_feeds.py`
`ladyarcaders_candidates_of`, under the feed lock inside `run_check`):

1. **Highest known** = the highest of `FLOOR` (**24**), every `source_ref` of a `ladyarcaders` marathon on the list
   (any feed or none, paused and over ones count), every ref staff removed (`ignored`), every **found** record in
   `seen`. Empty records do not raise it.
2. **To probe** = the next `PROBE_AHEAD` (**3**) numbers above it, skipping a number whose empty record is younger
   than `marathon_feed_hours × EMPTY_RETRY_CHECKS` (**4** → 24 h at the default 6 h).
3. **Probe**, one calendar GET per number, in order: **VEVENTs** → a found record `{ref, name, starts_at, ends_at}`
   (first run's start, last run's end); **200 with nothing / no VEVENT / not a calendar** → an empty record `{ref,
   empty_at}`; **404** → stop this check's probe; **any other status** → the check fails (`checks_failed`, the third
   is `marathon.feed_stale`).
4. The answers replace the same numbers in `seen` (`merged`, capped at `SEEN_LIMIT`) and are written BEFORE the
   candidates are judged.
5. **Candidates** = every found record whose end (else start) is ahead of now or within `marathon_feed_recent_days`
   (recent by END, like horaro.net and Oengus), URL `schedule_page` — which `read_url` reads back, so `create_marathon`
   resolves it. `run_check` then does what it does for every source: adopt, `fresh()` (never twice, never a removed
   one), and **`add_candidate`** — the quiet row, the staff notice once the calendar yields runs (v171). A found
   event's calendar HAS runs, so under `published` the notice posts on the add's own first read.

**Look again** clears `seen` (the existing Oengus path — `mf.seen_of` counts these records) and answers
`FEED_REPROBE` (*It asked ladyarcaders.com about the next events again (N remembered before).*); the next check
probes from the floor / the list again. **Forget ignored** leaves `seen` alone.

**Seed** `Seed("ladyarcaders", LADYARCADERS_FEED, "ladyarcaders", "Lady Arcaders")`, appended to `SEEDS`, through the
once-ever `marathon_feed_seeds` marker (`seed_feeds` skips a login that has no channel row and does NOT mark it). ⚠️
**No `ladyarcaders` channel row exists live today** (research doc, 12:1x read), so nothing seeds on deploy; **the
first boot after staff add the `ladyarcaders` channel row on the Go-live page (marathons on) seeds the feed and its
first check probes 25–27.** A row added while the bot runs waits for the next boot (the seed runs once per process).

**Doors:** the Add a feed pick `ladyarcaders` (*Lady Arcaders — looks for their next event's calendar on
ladyarcaders.com*), guessed from the `ladyarcaders` login on the site and in the Discord modal; the site's pick help
line; the feed drawer's memory line (*Remembers what N Lady Arcaders event number(s) answered; one with no calendar
yet is asked again after four checks. **Look again** asks them all now.*); the Source column word *Lady Arcaders*.
Every move a feed already has (Check now, Pause, Add/Suggest, Look again, Forget ignored, Rename, Move, Event mode,
Remove) works unchanged — staff final say is the existing feed surface.

## Deviations

1. ⚠️ **The calendar is `/events/<n>/schedule/calendar/`, not the brief's `/events/<n>/calendar/`** — that path is a
   404 for 24 and 25 alike (measured). `read_url` still accepts the brief's form (it names the same event); every read
   goes to `…/schedule/calendar/`.
2. ⚠️ **No hosts or commentators.** The calendar carries only the performers; the HTML page has Host / Commentator
   badges, but reading HTML was not built (a second, fragile read per marathon). Runs carry runners only; a BaF host
   on a Lady Arcaders marathon is NOT matched by this reader. A later build could parse the page's badges.
3. **The org's own segments stay runs, with nobody on them** — `Lady Arcaders` as a performer is dropped
   (`ORG_NAMES`), so *Welcome to LASS 2026!* is on the schedule but matches no member.
4. ⚠️ **Existence is judged by the calendar only.** #25's calendar answered 200-empty and its page redirected to
   `/opportunities/`; an event that exists but has not published a schedule was not observed, so the probe cannot
   tell "unpublished" from "no such event" and does not try (no page read). An empty calendar, a calendar with no
   VEVENT and a non-calendar page are all *empty* — remembered and asked again after the gap. So an LA event is found
   only once its calendar has runs, and staff cannot **Add** one earlier either (`resolve` refuses an empty calendar)
   — unlike a GDQ draft. Its dates are then known at once.
5. ⚠️ **`FLOOR = 24` (not in the brief).** With nothing known, "above the highest known" would start at 1 and take ~8
   checks (two days) to walk the history, re-probing old events. 24 is the newest event seen live (Super Showcase
   2026). It is a code constant, not a settings key: staff move the probe by adding a higher event by link (it counts
   as known) and reset it with **Look again**. Flagged for checklist 33 — the reviewer may want it a key.
   **Superseded at the merge (2026-09-26, branch `merge-marathon-sources`):** it IS a key now,
   `marathon_ladyarcaders_floor` (int, default 24), read per guild where the probe read `FLOOR`.
6. **Found records stay in `seen` and stay candidates while recent** (like the Oengus memory), so a failed add is
   retried, an adopted row keeps its feed, and **Forget ignored** can re-add — with no second probe.
7. **A probe that fails mid-way writes nothing from that check** (the error is raised before `merged`); earlier
   memory is kept. The next check probes the same numbers.
8. **`mf.seen_of` was NOT changed.** It already tolerates the new record shapes (it reads `ref` and ignores the rest),
   which is all Look again, `feed_moves` and the API's `seen_count` need; the LA code reads the raw records itself
   (`mf.list_of(feed["seen"])`). ⚠️ So a future caller that rewrites `seen` through `seen_of` + `seen_after` would
   strip an LA record's fields — only the Oengus path does that, and only on an Oengus feed.
9. **`ScheduleClient` grew `_open()`** (the session, factored out of `_aiohttp_request`), `_aiohttp_text`, `text()` and
   a `text_request=` injection — the smallest way to share the session; the JSON path is unchanged.
10. **Words changed** (staff overrides kept): `marathon_unknown_site`'s default is now *I can read the GDQ and RPG
    Limit Break trackers, horaro.net schedules, Oengus marathons and Lady Arcaders calendars — that link is none of
    them.*; `marathon_feed_recent_days`'s help names *a Lady Arcaders event* (mock mirrored). **Left alone on purpose,
    for the conductor to reword ONCE after the three sibling merges** (each sibling would otherwise rewrite the same
    lines): `mf.UNKNOWN_PICK` and the mock's `unknown_source` refusal (list the picks), `mf.ADD_FEED_SOURCE` (the
    Discord modal label, 45-character cap — the pick is pre-filled from the login anyway), the `marathon_feeds` key's
    help, the site's `FEED_ADD_NOTE`. New answer constant `FEED_REPROBE` (a panel answer, not posted — the Oengus
    Deviation 11 precedent), new site constant `FEED_PROBE_NOTE`.
11. **`AddFeedModal.source` `max_length` 10 → 20** — `ladyarcaders` is 12 characters and could not be typed.
12. **`PICK_NAMES` gained `ladyarcaders` → *Lady Arcaders***, so a feed added on a differently named row is still
    called Lady Arcaders.
13. **`.gitattributes` gained `*.ics -text`** so the fixture keeps the live CRLF bytes (the repo normalises text to
    LF); the parser is also tested on LF and CR.
14. **Mock ids are 20** (channel row, feed, marathon) so the three sibling builds' samples do not collide. The mock
    marathon *Lady Arcaders Super Showcase 2026* has no runs in the mock, so its row reads *0 of 0 · not published* —
    mock-only cosmetics. The mock's `feedCheck` still acts on the GDQ feed only; its Look again does not clear `seen`
    (the Oengus mock precedent).
15. **Tests** (mirror rule): `tests/test_marathon_ladyarcaders.py` (new, the parser, mapping, reader, probe);
    `tests/test_marathon_sources.py` +4 functions (read_url forms and refusals, page and words, the text read);
    `tests/test_marathon_feeds.py` +2 (seed / pick / words, Look again offered) and the seed test now checks the first
    three seeds by position; `tests/cogs/content/test_marathon_feeds.py` +10 (seed once; a check probes 25–27, adds the
    one that answers, remembers the empties; within the gap nothing is probed, after it the same three; a find moves
    the window; a 404 stops; a staff-pasted #30 moves the probe to 31–33; the notice once the calendar yields runs;
    Look again re-probes; Add a feed ▸ ladyarcaders; a 503 is a failed check that keeps the memory);
    `tests/api/tools/test_marathon_feeds.py` — the `sources` list assertion checks the first four and that
    `ladyarcaders` is offered (so the siblings' picks do not break it).
16. **`ruff format --check` fails on the touched shared files at `a3ac5132` already** (`marathon_feeds.py`
    `FEED_CHECKED`, `settings_store.py` `GOLIVE_TEMPLATE`, the cog's `feed_details` call, …, the Oengus Deviation 16
    precedent); whole files were NOT reformatted. Every line this build added is format-clean; the two new files are
    formatted; `ruff check .` is clean.

## What was NOT verified

1. ⚠️ **Nothing met Discord or Fly.** The seed, the probe, the quiet add and the notice ran only against the suite's
   fakes (`FeedClient.text`); `/event` ▸ Marathons… ▸ Feeds… ▸ Add a feed… with `ladyarcaders` only through
   `create_feed`.
2. ⚠️ **The bot's own client never read ladyarcaders.com** — the six GETs above were `urllib` on the build machine;
   `ScheduleClient._aiohttp_text` (aiohttp `response.text(errors="replace")`) is exercised only through its injected
   fake. Not from Fly.
3. **What an existing-but-unpublished event answers** — not observed (Deviation 4). If it answers a named calendar
   with no VEVENT, the feed treats it as empty and waits, which is safe.
4. **The live `ladyarcaders` channel row** does not exist (research, 12:1x); the seed was proven on a test row.
5. **Cost:** at most 3 calendar GETs per check (every 6 h), and 0 once the next three are remembered empty — then 3
   per 24 h; plus the add's resolve + read (two GETs) per new event. Rate limits not measured.
6. **The page** was rendered in headless Chrome (`chrome.exe --headless=new`, raw CDP from node) against this
   branch's mock on `MOCK_PORT=8808`: the Marathons list (*Lady Arcaders Super Showcase 2026* · *Lady Arcaders ·
   feed*), **Sources…** (four rows, *Lady Arcaders* · *Lady Arcaders*), the Lady Arcaders feed drawer (*Read from:
   **Lady Arcaders***, the memory line, **Look again**), and **Add a feed…** with the `ladyarcaders` pick and its help
   line — **zero console errors**, two screenshots looked at. Nothing was submitted in a browser; the writes were
   checked by `check.mjs` and the tests.
