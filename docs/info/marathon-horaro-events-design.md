# Marathon feed `horaro_events` — find a channel's events on horaro.net (Fast Paced Events)

> ✅ **2026-09-26 13:4x — LIVE as v173 13:35** (merge `62aefd31`; release commit `5a66acd2` (`release.json` v173 at `aee13ffe`); ONE fast-forward of `main` to `merge-marathon-sources` `282ce0ee`; boot `database ready` 20:35:43Z, `synced 33 app commands` 20:35:43Z, `logged in as Black_Bloc` 20:35:46Z, no Traceback, `/health` 63 ms — `deploys.log`'s v173 line). After the deploy the session added channel row **9 `fastpacedevents`** (marathons ON, spotlight and announce OFF) and feed **6 *Fast Pace*** (horaro events) through the owner's browser session; its first check found **0** — nothing announced yet, as the research said. So this reader has NOT yet met a live event from Fly. Sweeps `HE-a…d` are the owner's. The status line below is history.

> **Audience:** the conductor, reviewers and the next build agent. **Status:** TRACKED · 🔨 **BUILT on branch
> `marathon-horaro-events`** (off `main` `a3ac5132`; commits `053ebcfa` code + tests + fixtures, `87ddd4ba` site +
> mock, and the docs commit) — **NOT merged, NOT deployed, nothing has met Discord or Fly.** **Last verified:
> 2026-09-26 ~12:3x Phoenix** — the API shapes below were read live that day from the build machine (Python `urllib`,
> plain User-Agent `black-bloc-research/1.0`, one GET per URL, eight GETs in all, listed under *What was NOT
> verified*). Schema **68, unchanged**; registry keys **unchanged**; `check.mjs` **22 pages, 252 routes** (unchanged).
> **NOT checked:** the bot's own `ScheduleClient` (aiohttp, `BROWSER_AGENT`) against `/-/api/v1/events`; anything from
> Fly (KI-30's datacenter wall); horaro.net's rate limits; the total event count beyond a bracket (3,600–5,000);
> whether horaro's `name` search also matches anything but the event name beyond the two probes below. Secret NAMES
> only — there are none here.

## The ask, verbatim (owner, 2026-09-26 12:3x Phoenix)

*"Build them all now"* — after [`marathon-orgs-research-2026-09-26.md`](marathon-orgs-research-2026-09-26.md). This
branch is **Fast Paced Events**: a horaro.net feed that FINDS a channel's events, instead of watching one fixed slug
(FPE makes a new horaro.net event per marathon — `fpff3`, `fpfp2025` — so the existing `horaro` feed, built for ESA's
one-event-many-schedules shape, would never see the next one). The two sibling sources (`marathon-fastestfurs`,
`marathon-ladyarcaders`) are other branches.

## The API, as read 2026-09-26

| GET | Answer |
|---|---|
| `https://horaro.net/-/api/v1/events` | 200, 9,249 B. `{data: [20 events], pagination: {offset: 0, max: 20, size: 20, links: [{rel: "next", uri: "…/events?offset=20"}]}}`. Each event: `{id, name, slug, link, description, owner, website, twitter, bluesky, twitch, links: [{rel: self}, {rel: schedules}]}`. **Paged** (default `max` 20; `max=100` is accepted); the order is not by date (first rows: `mshr`, `qsmp2`, …). |
| `…/events?offset=2000&max=100` · `…?offset=3500&max=100` · `…?offset=5000&max=100` | 100 · 100 · **0** rows (the last carries only a `prev` link). So horaro.net lists **between 3,600 and 5,000 events** — a full walk is ≥ 36 pages of `max=100` (~1.6 MB) every check. No total count is given. |
| `…/events?name=Fast%20Pace` | 200, **8 events**, one page (`links: []`): `fpff` (`fastpacedevents`), `fpffs2` (`fastpacedevents`), `fpff3` (`fastpacedevents`), `fpfh` (**`tgh_sr`**), `fpfh2023` (**`FastPacedEvents`**), `fpfp2022` (`fastpacedevents`), `fpfp2023` (`FastPacedEvents`), `fpfp2025` (`fastpacedevents`). Research used `name=fast` (lower case) and found the same, so the search ignores case. |
| `…/events?name=fastpacedevents` · `…?name=Fast%20Paced%20Events` | 200, **0 events** each — the search is a substring of the event NAME only; it does not match `twitch`, and FPE's brand is not in its events' names (*Fast Pace for …*). |
| `…/events/fpff3/schedules` | 200, the shape the `horaro` feed already reads: `{data: [{id, name: "Fast Pace for Friendspace 3", slug: "schedule", timezone: "America/Detroit", start: "2026-08-22T10:00:00-04:00", start_t, website, twitter, twitch: "fastpacedevents", bluesky, description, setup, setup_t, updated, link: "https://horaro.net/fpff3/schedule", columns: ["⠀ ", "⠀ ", "Runner", "Game", "Category", "Platform", "Host"], items: [12 × {length, length_t, scheduled, scheduled_t, data}], links}]}`. |

**`twitch` is a bare login in every event read (28 of 28), in either case** — never a URL. The reader still accepts
`twitch.tv/<login>` or `@login` (`twitch_of`), in case one is ever written that way.

**Does horaro list an upcoming FPE event today? No.** The newest FPE event is `fpff3` (2026-08-22, over); the other
seven are 2021–2025 by their names and the research's dates. Only `fpff3`'s schedules were read by this build.

## The query decision

**Search by the FEED'S NAME, not a full walk.** A full walk is ≥ 36 pages every six hours per feed, against a
site whose size is not published — not sane. The search is one GET (up to `HORARO_EVENT_PAGES` = 3 pages of 100).
Because it matches event names only, the feed's name must be words the channel's events are called by — for FPE
**"Fast Pace"**, not "Fast Paced Events" (measured: 0 results). The name is staff-editable through the existing
**Rename…** move (site and Discord), so staff can fix a search that finds nothing; a blank name is refused in words
(`NO_QUERY`) and the client never sends an empty search (which would list the whole site). Deviation 1.

## The design, as built

- **Source** `horaro_events` (`marathon_feeds.HORARO_EVENTS_FEED`), a fifth feed source beside `horaro` (which is
  unchanged, for ESA). `feed_ref` = the channel's login (the Oengus precedent — `UNIQUE (guild_id, source, feed_ref)`
  allows one per channel); **Move to channel…** rewrites it. The match reads the channel row's CURRENT login, the ref
  is the fallback.
- **A check** (`marathon_horaro_events.check`): one `ScheduleClient.horaro_events(<feed name>)` search; the events whose
  `twitch` equals the login case-insensitively are **ours**; each of ours not yet *settled* in memory gets ONE
  `horaro_schedules(<slug>)` read (at most `READS_PER_CHECK` = 20 per check); every listed event is remembered.
- **Memory** is `marathon_feeds.seen` (JSON, no schema change): `{ref: <event slug>, twitch}` for every listed event,
  plus — for ours, once read — `schedule` (the first listed schedule's slug), `name`, `starts_at`, `ends_at` (from
  `horaro_span`) and `url` (the schedule's `link`). An event is *settled* once it has a `schedule`; one read before it
  had any schedule is read again next check. A failed schedules read is not remembered (logged at info) and is read
  again next check; it does not fail the check. A failed SEARCH fails the check as any list failure does
  (`checks_failed`, the third is stale). Capped at `SEEN_LIMIT` 2,000, newest kept (`seen_after`).
- **Candidates** (`candidates`): one per event that this check's search lists, whose remembered `twitch` is the login,
  that has a schedule, and whose schedule ends ahead of now (or within `marathon_feed_recent_days`) — "recent" is by
  END, like `horaro` and `oengus`. `ref` = **`<event>/<schedule>`** (e.g. `fpff3/schedule`), `name` = the event's name,
  `url` = `https://horaro.net/<event>/<schedule>`.
- **Added** through the SAME `add_candidate` → `create_marathon` path as every feed: `read_url` reads the URL as
  `(horaro, "<event>/<schedule>")`, so the marathon is a plain **`horaro`** marathon whose `source_ref` equals the
  candidate's ref — dedupe (`marathons_by_ref`), adoption and Remove's `ignored` all key on it. The v171 rule holds:
  the row is added quietly; the staff notice posts once a read finds runs (`marathon_feed_notice_when` = published).
- **Look again** clears `seen` (the existing generic path — any feed that remembers records) and checks at once; its
  answer says `REREAD` (*It read every horaro.net event it had looked at again (N remembered before).*) instead of the
  Oengus sentence.
- **Seed** `Seed("fastpacedevents", HORARO_EVENTS_FEED, "fastpacedevents", "Fast Pace")`, appended to `SEEDS`. The live
  bot has **no** `fastpacedevents` channel row today (research, 12:1x), and the seed is once-ever per LOGIN
  (`marathon_feed_seeds`) and is only marked when the row exists — so the marker is untouched until staff add the row,
  and **the first boot after staff add `fastpacedevents` on the Go-live page (marathons on) seeds the feed**. ⚠️ The
  seed runs once per PROCESS (`cog.feeds_seeded`), so a row added while the bot runs is seeded at the NEXT boot, not
  at once — or staff add the feed by hand (**Add a feed…** ▸ horaro.net events).
- **Words / site:** pick `horaro_events` — *horaro.net events — finds this channel's events on horaro.net, searching by
  the feed's name (Fast Paced Events' home)*; the site's help line under the pick says to set **Name** to what the
  events are called; **no slug field** (it shows only for the fixed-slug `horaro` pick); the pick is guessed for the
  `fastpacedevents` login (site `PICK_GUESS`, Discord `guess_pick` through `SEEDS`). The Sources list's source word is
  **horaro.net events**; the marathons it adds read *horaro.net* like any horaro marathon. The feed drawer's memory
  line says *horaro.net event(s)* for this kind. No new settings key: no new sentence is POSTED (the notices use
  `marathon_feed_added_template` / `…_suggest_template`); the new words are panel answers and site constants, the
  Deviation-11 precedent of §H.
- **Mock:** channel row **12** `fastpacedevents` and feed **12** (`horaro_events`, *Fast Pace*, add mode, remembering
  `fpff3` with its real schedule span and `fpfh` as another channel's) — no marathon, true to today.

## Deviations

1. ⚠️ **The search is by the feed's NAME, so the seed is named "Fast Pace", not "Fast Paced Events"** (the brief's
   seed name). Measured: `name=Fast Paced Events` and `name=fastpacedevents` return 0 events; `name=Fast Pace` returns
   all 8. A feed added by hand with a blank Name takes the channel's display name and will find nothing until renamed
   — the pick's help line says so. The notice therefore reads *Fast Pace has a new event: **Fast Pace for …***.
2. ⚠️ **The candidate ref is `<event>/<schedule>`, not the bare event slug.** `create_marathon` only accepts a URL
   `read_url` reads, and `read_url` reads horaro.net as `<event>/<schedule>` (`horaro.net/<slug>` alone is not a
   schedule link). Every dedupe (`known`), adoption and Remove-ignore compares the candidate ref with the marathon's
   `source_ref`, so they must be the same string. The MEMORY (`seen`) is keyed by the bare event slug, as the brief
   said.
3. **`seen` records carry more than `{ref, twitch}` for the channel's own events** (`schedule`, `name`, `starts_at`,
   `ends_at`, `url`) — horaro's event list carries no dates, so without them every check would re-read every event's
   schedules. `marathon_feeds.seen_of` (the shared reader) still reads these records as `{ref, twitch}`, so
   `seen_count`, Look again's offer and the Oengus path are unaffected; this module reads them with its own `seen_of`.
4. **The first listed schedule is the event's marathon** — one Candidate per event, as the brief said. An event with
   two schedules (ESA-style streams) gets only its first. FPE has had one per event (`schedule`) in every event read.
5. **An event whose schedules list is empty is re-read each check** (≤ 20 reads per check) until it has one — so an
   event created before its schedule is still found. The listed-but-not-ours events are remembered as `{ref, twitch}`
   and never read.
6. **Candidates need the event in THIS check's search.** An event renamed out of the search, deleted, or re-assigned
   to another `twitch` stops being a candidate (the marathon already added stays).
7. **`ScheduleClient.horaro_events` and `horaro_next` live in `marathon_sources.py`** (the client), placed beside
   `horaro_schedules` / `horaro_span`, not at the end of the class, to keep the sibling branches' hunks apart. It
   follows `pagination.links[rel=next]` only while the link stays on `https://horaro.net/`, at most 3 pages of 100.
8. **The Discord Add-a-feed modal's *Read from* field went from `max_length=10` to 20** — `horaro_events` is 13
   characters and would not fit. ⚠️ **Merge hazard:** a sibling branch adding a long pick word makes the same edit.
   The field's label (`ADD_FEED_SOURCE`, *Read from — gdq, rpglb, horaro or oengus*) was NOT extended — Discord caps a
   label at 45 characters — and `UNKNOWN_PICK` and the site's `FEED_ADD_NOTE` were not reworded (shared sentences the
   sibling branches also touch; the conductor may reword them once at merge). The pick is still offered: the site's
   select lists it and the modal's default is guessed for `fastpacedevents`.
9. **`tests/api/tools/test_marathon_feeds.py`** asserted the exact source list; it now asserts the first four and that
   `horaro_events` is offered, so the siblings' appends do not collide on one line.
10. **`tests/test_marathon_feeds.py`'s seed test** read `SEEDS[-1]` as SS4C; it now reads `SEEDS[2]` and lists the
    FPE seed.
11. **`ruff format --check`** fails on `marathon_feeds.py`, `cogs/content/marathon_feeds.py`, `tests/test_marathon_feeds.py`,
    `tests/cogs/content/test_marathon_feeds.py` and `tests/api/tools/test_marathon_feeds.py` — every flagged hunk is
    pre-existing code (the §H Deviation-16 finding); not reformatted. The new files and every added line are
    formatted; `ruff check .` is clean.

## What was NOT verified

1. ⚠️ **Nothing met Discord or Fly.** The seed, the check, the quiet add, the notice and Look again ran only against
   the suite's fakes (`FeedClient` with a patched `horaro_events`); the modal only through `create_feed`.
2. ⚠️ **The bot's own `ScheduleClient` never read `/-/api/v1/events`.** The fixtures came from `urllib` on the build
   machine; the client is proven on a fake `request`. **Not from Fly** — KI-30 is untested on this route.
3. **Live reads, 2026-09-26 ~12:3x Phoenix, eight GETs:** `…/events`, `…/events?name=Fast%20Pace`,
   `…/events/fpff3/schedules` (the three the brief named), `…?name=fastpacedevents` and `…?name=Fast%20Paced%20Events`
   (does the search match `twitch` or the brand?), and `…?offset=5000&max=100`, `…?offset=2000&max=100`,
   `…?offset=3500&max=100` (how big is a full walk?). Fixtures: `horaro_events_search.json` (3 of the 8 — `fpff3`
   `fastpacedevents`, `fpfh2023` `FastPacedEvents`, `fpfh` `tgh_sr`; `owner` dropped), `horaro_fpff3_schedules.json`
   (4 of 12 items).
4. **No FPE event is upcoming** — so no live proof exists that a NEW FPE event appears in the search before its
   schedule is published; the re-read-until-a-schedule rule (Deviation 5) is the hedge.
5. **The live `fastpacedevents` row does not exist**, so the seed's keying on that login is from the research doc's
   Linktree/horaro reads, not from a live row.
6. **Cost:** one search GET per 6 h (+ up to 20 schedules GETs on the first check — 7 for FPE today — and one per
   unsettled event after). horaro.net's rate limits were not measured.
7. **The page** was rendered in `chrome-headless-shell` 149.0.7827.22 over raw CDP against this worktree's mock on
   `MOCK_PORT=8807`: the Sources list (*Fast Paced Events* · *horaro.net events*), the feed drawer (*Read from:
   **horaro.net events***, *Remembers 2 horaro.net event(s)…*, **Look again**), and Add a feed… with the horaro.net
   events pick (its help line; the slug field hidden) — **zero console errors**, one screenshot looked at. Nothing
   was submitted in a browser.

## Follow-up — owner match + several words (2026-09-27)

> **Status:** 🔨 **BUILT on branch `horaro-events-owner`** (off `main` `7f7b99e7`, v178 live; commits `99b31fae` code +
> keys + tests, `9dea3428` site + mock, then the docs commit) — **NOT merged, NOT deployed, nothing has met Discord or
> Fly.** **Last verified: 2026-09-27 ~15:3x Phoenix** — the API rows below were read live that afternoon from the build
> machine (Python `urllib`, plain User-Agent `black-bloc-research/1.0`, one GET per URL, six GETs). Schema **75,
> unchanged**; registry keys **602 → 615**; `check.mjs` **22 pages, 265 → 266 routes**.

**The ask (owner, 2026-09-27 15:1x, through the conductor):** RGL's ~60 horaro.net events are owned by the horaro
account **`RGLtvMarathons`**; a feed searching **RGL** finds 5 of their 10 2026 events and misses Retrothon (no *RGL* in
its name, event-level `twitch` empty), Kessel Run, MEGAmorial, RPGLtv Gauntlet and NINJULYDEN
([`marathon-orgs-research-2026-09-26.md`](marathon-orgs-research-2026-09-26.md) ▸ *Retro Gaming Live*). So: keep an
event whose **owner** is the feed's owner, and let a feed search **several words**.

### The API, as read 2026-09-27

| GET | Answer |
|---|---|
| `…/-/api/v1/events?owner=RGLtvMarathons&max=100` | 200, 43,668 B, **100 events from many owners** (`AndreDK7`, `ArcadiaGamesBR`, …; first row `mshr`, owner `Player_Next_Level`) with a `next` link — the **`owner` parameter is ignored**; this is the unfiltered list. **The API cannot filter by owner.** |
| `…/-/api/v1/users/RGLtvMarathons/events` | **404** — no per-user route. |
| `…/events?name=Retrothon&max=100` | 200, **9 events, every one `owner: RGLtvMarathons`**: `retrothon2019`…`retrothon2025`, `retrothon26`, `rgltvretrothon`. Event-level `twitch` is **`null` on `retrothon26` and `retrothon2022`**, `RetroGamingLiveTV` (mixed case) on `retrothon2021`, `retrogaminglivetv` on the rest. |
| `…/events?name=RGL&max=100` | 200, **49 events**, one page; owners `RGLtvMarathons`, `Germench`, `Kongcakes`, `LRock617` — the search still lists other people's events, which the match must drop. |
| `…/events?name=RGLtv&max=100` | 200, **36 events, all `RGLtvMarathons`** (first row `rgltv10`, event-level `twitch: null`). Every one also contains *RGL*, so an `RGL` search already lists them (substring). |
| `…/events/retrothon26/schedules` | 200, one schedule `schedule`, **schedule-level `twitch: retrogaminglivetv`**, `start` 2026-04-18T12:00-04:00, `America/New_York`, link `https://horaro.net/retrothon26/schedule`. |

**`owner` is present on every event in the list payload** (all 194 rows read), as the research said. Because the API
cannot filter by it, **the feed keeps the name search** and applies the owner as a MATCH, not a query.

### As built

- **Where the settings live — `marathon_feeds.seen`, no schema step.** A horaro.net events feed's search is ONE record
  at the head of its `seen` JSON: `{"search": {"owner": "RGLtvMarathons", "words": ["RGL", "RGLtv", "Retrothon"]}}`.
  It has no `ref`, so `marathon_feeds.seen_of` (the shared reader behind `seen_count`, Look again's offer and the
  Oengus path) and this module's own `seen_of` both skip it. `feed_ref` stays the channel login; `name` stays the
  feed's display name. `hre.search_of` reads it, `hre.search_with` rewrites it (dropped when owner and words are both
  blank), `hre.search_kept` puts it back at the head of every memory the check writes, and `hre.forgotten` is Look
  again's `seen` — every event forgotten, **the search kept**. Every writer runs under the per-feed lock, so a check
  cannot write back an older search.
- **Owner match** (`hre.is_ours`): an event is the channel's when its `twitch` is the login (as before) **or** its
  `owner` equals the feed's owner, both case-insensitive. `to_read` and `candidates` take the owner; `candidates` no
  longer re-checks the remembered `twitch` (an owner-kept event's memory says `twitch: ""`) — this check's own listing,
  matched with the owner, decides.
- **Several words** (`hre.words_of`, `hre.queries`, `hre.searched`): up to **5 words** (`WORDS_LIMIT`), each ≤ **40**
  characters (`WORD_LENGTH`), split on commas or new lines, repeats dropped case-insensitively. Each word is ONE
  `ScheduleClient.horaro_events` search (unchanged, ≤ 3 pages); the results are de-duplicated by slug. **No words →
  the feed's name is the one search** (FPE's *Fast Pace* feed is unchanged). A failed search of any word fails the
  check, as one failed search did before.
- **Owner** (`hre.owner_clean`): whitespace collapsed, ≤ **60** characters (`OWNER_LENGTH`), blank clears it.
- **One writer:** `cogs/content/marathon_feeds.set_feed(owner=, words=)` → `set_search` — refused in words on any
  other kind of feed (409 `not_horaro_events`), too many / too long words (422 `bad_words`), too long an owner (422
  `bad_owner`); one `marathon.feed_changed` row carrying `words` and/or `owner`; an unchanged value says nothing.
- **Site:** `PATCH /api/marathons/feeds/{id}` takes `owner` (text) and `words` (text or list; anything else is 422
  `bad_words`). Each feed row carries `owner`, `words` and `searches` (what is actually searched — the words, else the
  name); all three are `null` for other kinds. The feed drawer draws **Search words** (placeholder: what it searches
  today) and **Owner** under Auto-track, only for a horaro.net events feed (`marathon-words.js:feedSearchFields`);
  each saves on change. The Add-a-feed pick's help line says the drawer takes them once added.
- **Discord:** the `/event` ▸ Sources feed card of a horaro.net events feed shows *Searches horaro.net for **…**.* and
  (with an owner) *Also keeps every event the horaro.net account **…** owns.*; a **Search words…** button (row 4)
  opens a two-box modal (words, owner) prefilled with the current values.
- **Every word a key** — 13 Marathons text keys: `marathon_feed_search_move`, `_search_title`, `_words_label`,
  `_owner_label`, `_search_line`, `_owner_line`, `_words_said`, `_words_cleared`, `_owner_said`, `_owner_cleared`,
  `_search_refused`, `_words_bad`, `_owner_bad` (registry `MARATHON_WORDS`, mock rows, `labels.js`).
- **Mock:** feed 12 (*Fast Pace*) is unchanged (no search record — true to today); the PATCH, the row fields, the
  keyed answers and refusals, `seen_count` without the search record and the horaro.net Look-again sentence are
  mirrored. `check.mjs` gains one contract entry (`PATCH /api/marathons/feeds/{feed_horaro_events_id}` = 12).

### Deviations

1. **No owner query** — the API ignores `?owner=` (measured above), so the brief's "list by owner" branch does not
   apply; the owner is a match on the name-search results. ⚠️ **An RGL event whose name shares none of the feed's
   words is still missed**, owner or not. A whole-site walk remains the only complete version (rejected for cost).
2. **The settings ride in `seen`, not a new column** (the brief's preference). Consequence: anything that ever writes
   `seen` for this kind must keep the head record — today that is `hre.check` (via `search_kept`), Look again (via
   `hre.forgotten`) and `set_search`. A future writer that forgets it would silently clear the search.
3. **The site's field labels and help lines are site constants** (`FEED_WORDS_FIELD`, `FEED_OWNER_FIELD` and their
   help in `marathon-words.js`), like every other drawer label on that page; the 13 keys cover what the BOT says
   (Discord card, button, modal, answers, refusals — the site shows the bot's answers).
4. **The API's malformed-body refusal** (`BAD_SEARCH`, a number or object given for `owner`/`words`) is an API constant
   like `BAD_ACTIVE`, not a key.
5. **`RGLtv` as a search word adds nothing** beyond `RGL` (every `RGLtv` event name contains `RGL`; measured 36 ⊂ 49).
   It costs one extra GET per check and is harmless; the conductor's settings below keep it because the brief named
   it. Words that WOULD add coverage (the research's misses): `Kessel`, `MEGAmorial`, `RPGLtv`, `NINJULYDEN` — the
   limit is five words.
6. **Owner-matched history is read ≤ 20 events per check** (`READS_PER_CHECK`, unchanged). With the owner set, RGL's
   whole horaro history across the words (~55 events) counts as the channel's, so the first **three** checks read
   schedules (20 + 20 + the rest) and an upcoming event may only become a candidate on the second or third. Search
   order is horaro's, not by date.
7. **`ruff format --check`** still fails on `api/tools/marathon_feeds.py`, `cogs/content/marathon_feeds.py`,
   `settings_store.py` and the three feed test files — every flagged hunk is pre-existing (Deviation 11 above); none is
   this build's.
8. **Key-count merge hazard:** `tests/test_settings_store.py` asserts the exact registry size (now **615**); any
   sibling branch adding keys edits the same line.

### What was NOT verified

1. ⚠️ **Nothing met Discord or Fly.** The card lines and the button ran through `feed_card` in the suite; the modal
   class was never submitted by an interaction; the checks ran against fakes.
2. ⚠️ **The bot's own `ScheduleClient` never searched these words** — the fixtures came from `urllib` on the build
   machine (`horaro_rgl_search.json`: `retrothon2025`, `retrothon26`, and Germench's `interglitches24restream`;
   `horaro_retrothon26_schedules.json`: 3 of its items). KI-30 is untested on this route from Fly.
3. **No browser rendered the drawer** — the fields are proven through the pure `feedSearchFields` (node test) and
   `node --check`; `check.mjs` drove the PATCH against the mock on port 8820.
4. **Whether live row 7 already has a feed** was not read (the conductor checks before adding one — one feed per
   channel).
5. horaro.net's rate limits: not measured; the RGL settings below cost 3 searches per check (≤ 9 GETs) plus the
   schedule reads in Deviation 6.

### The RGL settings — for the conductor, AFTER the deploy (nothing here was applied)

On the live site, Events ▸ **Sources…**:

1. If channel row **7** (`retrogaminglivetv`) has **no feed**: **Add a feed…** ▸ the *RetroGamingLiveTV* row ▸ *Read
   from* **horaro.net events**, Name **Retro Gaming Live** (the notices read *Retro Gaming Live has a new event…*; its
   first check at add searches that name and finds 0 — harmless). API form: `POST /api/marathons/feeds`
   `{"spotlight_id": 7, "source": "horaro_events", "name": "Retro Gaming Live"}`. If row 7 already has a feed of
   another kind, remove it first (one feed per channel).
2. Open the feed's drawer: **Search words** = `RGL, RGLtv, Retrothon`; **Owner** = `RGLtvMarathons`. API form:
   `PATCH /api/marathons/feeds/<id>` `{"words": "RGL, RGLtv, Retrothon", "owner": "RGLtvMarathons"}`. Expected answer:
   *…searches horaro.net for **RGL, RGLtv, Retrothon** now. …also keeps every event the horaro.net account
   **RGLtvMarathons** owns now.* (Discord: the feed card ▸ **Search words…**.)
3. Press **Check now** three times (Deviation 6), then confirm the drawer's *Remembers N horaro.net event(s)…* and
   that `n6430th` (N64 30th, live until 09-29) is on the Marathons list — past events end outside
   `marathon_feed_recent_days` and are not added.
