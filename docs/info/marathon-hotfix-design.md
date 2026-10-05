# GDQ Hotfix — GDQueer and the other Hotfix shows, read from the schedule sheet

> **Audience:** the conductor, reviewers and future sessions touching marathon sources. **Status:** TRACKED ·
> 🔨 **BUILT on branch `marathon-hotfix`** (off `main` `6fc4a5a0`; commits `038a9113` reader + fixtures + tests,
> `7ea399b2` feed + key + schema + cog + routes, `21f6c24c` site + mock, and the docs commit) — **NOT merged, NOT
> deployed, nothing has met Discord or Fly.** Schema **79 → 80**, registry keys **694 → 695**, routes unchanged
> (`check.mjs`: *22 pages, 282 routes*). **Last verified: 2026-09-28** — against the two files the conductor fetched
> live that day (`tests/fixtures/marathon/gdq_hotfix_page.html`, `gdq_hotfix_sheet.csv`); the build itself made
> **no live request**. **NOT checked:** the bot's own client (aiohttp, `BROWSER_AGENT`) against gamesdonequick.com
> or docs.google.com, anything from Fly (KI-30's datacenter wall is untested on both hosts), whether Google answers
> the CSV with a redirect to `*.googleusercontent.com` today, rate limits. Secret NAMES only — there are none here.

## The ask, verbatim

Owner, 2026-09-28: *"https://gamesdonequick.com/hotfix/schedule its on this page, look at the show category for
GDQueer. Can we work with this? we might need a new function for parsing schedules from hotfix shows. We need a way
to give a list of shows we can then dynamically pull from this hotfix lift"* — and, 14:2x, on the times: *"the times
are all wrong, we need to take the times of each run and progress the clock ourself"*.

⏰ Games Done Queer starts **Sat 2026-10-03 1 PM Eastern (10 AM Phoenix)**.

## The shapes, as measured (the conductor, 2026-09-28)

- **The page** `https://gamesdonequick.com/hotfix/schedule` (Next.js) embeds ONE iframe,
  `https://docs.google.com/spreadsheets/d/e/2PACX-1vSxkh…MDNV/pubhtml?gid=728340068&single=true&widget=true&headers=false`
  — in the raw HTML (`&amp;`) and in the RSC payload (`\"src\":\"…\"`). No JSON endpoint.
- **The sheet as CSV**: `…/pub?gid=728340068&single=true&output=csv` → 200 `text/csv`, 6,668 B, 55 rows. A
  **two-row header**: row 1 `Show Date, Show Start (Eastern), Show, Host, Description,,,,`; row 2
  `,,,,Game,Category,Estimate,Runners,`. The 9th column (no header) is the runners' links. Data rows:
  `10/3/2026, 01:00:00 PM, GDQueer, GDQueer, Spyro Reignited Trilogy, Spyro the Dragon: 80 Dragons NBS, 1:08:00,
  Toronite, twitch.tv/Toronite`; co-op: runners `ProfessorBurtch, threepup`, links `twitch.tv/ProfessorBurtch,
  twitch.tv/threepup` (one quoted cell each). Categories carry commas (quoted) and trailing spaces.
- ⚠️ **"Show Start (Eastern)" is the SHOW's start, repeated on every row of that show-day — never a run's start.**
  Rows within a show-day are in running order; a run's start is the day's show start plus the estimates before it.
- Shows in the sheet that day: Fast Travel, Special Event, Creature Corner, Perilous Paths, Do All The Things, Random
  Number Generation, Out of the Box, Passion Project, Hidden Heroes, The Scenic Route, **GDQueer** (24 runs: 13 on
  10/3, 11 on 10/4, both 1 PM).
- The working copy of the CSV fixture has CRLF line ends (git stores LF); the parser is tested on both.

## The design, as built

**Source** `GDQ_HOTFIX = "gdq_hotfix"` (`marathon_sources.SOURCES`, last; *GDQ Hotfix*). `read_url` accepts
`https://[www.]gamesdonequick.com/hotfix[/schedule][/]` with an optional `#fragment`: `#GDQueer` → ref `gdqueer`,
`#Fast%20Travel` → `fast-travel`, `#gdqueer/2026-10-03` stays itself, no fragment → ref `""`. `schedule_page` →
the page with `#<ref>`.

**Reader** — `black_bloc/marathon_hotfix.py` (pure functions + one transport walk):

- `parse_hotfix(csv_text, shows)` → the **blocks** of the listed shows. Columns are found by NAME across the header
  rows (`show date`, `show start…`, `show`, `host`, `game`, `category`, `estimate`, `runners`; the links are the
  column after Runners); a sheet without Show Date / Show / Game is refused in words. Rows with no date, show or game
  are skipped. Shows match **case-insensitively, whitespace collapsed** (`show_key`: lower, spaces → `-`).
- **Grouping**: a show's rows, sorted by date (sheet order kept within a day), split where two dates are **more than
  one day apart** — GDQueer 10/3–10/4 is one block, a GDQueer block weeks later is another. `ref` =
  `<show-key>/<first date ISO>` (`gdqueer/2026-10-03`).
- **The clock**: each show-day starts at that day's show start (the first parseable *Show Start* of that show on that
  date) in **America/New_York** (`timezones.zone`, DST-aware — a December block is 18:00Z, October 17:00Z), and every
  run starts where the previous one ended (its estimate) — ⚠️ **since 2026-10-03 plus `marathon_setup_minutes`**
  (default 7; see *Follow-up 2026-10-03 — setup buffer* below). The next date restarts at its own show start. A day
  with no parseable start has runs with no times.
- **A run**: `game`, `category`, `run_seconds` = the estimate (`seconds_of`), `starts_at`/`ends_at` in UTC,
  `order` = place in the block, `external_id` = `<game-key>/<category-key>` (+ `#2`… for a repeat), **runners**
  split on commas with their Twitch logins from the link column (`twitch_login_from_url`, positional when the counts
  match, else by name), and the **Host** as a `host` person unless the host IS the show (GDQueer's host column says
  *GDQueer*).
- `block_for(blocks, ref, now)`: the block whose first date is the ref's; else the block that holds that date; a
  bare show (`gdqueer`) is the first block not over yet. A block the sheet no longer lists is
  `ScheduleError(unpublished=True)` (*the Hotfix sheet does not list gdqueer on 2026-10-03 any more*) — runs kept, no
  failure counted, no `schedule_stale` — because GDQ may clear aired shows from the sheet.
- `ScheduleClient.hotfix_sheet(page_url, fallback)` → `(csv, csv_url)`, `runs(gdq_hotfix, ref)` and
  `resolve(gdq_hotfix, ref)` (→ `(block.ref, block.show)`; ref `""` is refused: *the Hotfix page carries several
  shows — add the show's name after a #*). The client remembers the last good CSV URL in memory for its own
  schedule reads.

**The fetch and its guard** (`read_sheet` / `fetch`): GET the page → `sheet_url_of` (unescapes `&amp;`, `&`,
`\/`, finds the first `docs.google.com/spreadsheets/d/e/<key>/pubhtml`, keeps a numeric `gid`) → GET
`https://docs.google.com/spreadsheets/d/e/<key>/pub?gid=<gid>&single=true&output=csv` → check it is the sheet (the
header columns). **Redirects are followed by hand** (at most 5), and **every hop is checked BEFORE it is asked**
with `doc_import.hop_allowed` — now host-parameterised, same rules: `https` only, port 443 or none, no userinfo,
host exactly `gamesdonequick.com` / `www.gamesdonequick.com` / `docs.google.com` or ending `.googleusercontent.com`.
Anything else is *the GDQ Hotfix schedule sent Black Bloc to <host>, which it does not fetch*, unfetched. The
transport is `doc_import.aiohttp_hop` (one GET, `allow_redirects=False`, body read to one byte past the cap) with a
new `agent` parameter (the reader passes `BROWSER_AGENT`); cap **1 MB**, **20 s** per request, **45 s** for the
whole read (`asyncio.timeout`). Transport errors become `ScheduleError` (checklist 7).

**The fallback**: a page that cannot be read (a non-200, a timeout, a refused hop) falls back to the **last good CSV
URL** — on the feed (`marathon_feeds.sheet_url`, written whenever a check's CSV URL differs) or in the client's
memory — if that URL passes the same allowlist. ⚠️ **A page that answers 200 with no sheet iframe is a failure in
words, with NO fallback** (*the Hotfix page no longer embeds a schedule sheet*): that is the page changing, not a
hiccup, and staff should see it.

**Feed** `HOTFIX_FEED = "gdq_hotfix"` (`marathon_feeds.FEED_SOURCES`, last), pick `gdq_hotfix`, `feed_ref` = the
Hotfix page URL (a constant, so `UNIQUE (guild_id, source, feed_ref)` allows ONE Hotfix feed per server). Each check
(`cogs/content/marathon_feeds.py` `hotfix_candidates_of`): read the sheet (fallback = the feed's `sheet_url`),
remember the CSV URL, `parse_hotfix` with **`marathon_hotfix_shows`**, then `marathon_hotfix.candidates`: every
block whose END is ahead of now or within `marathon_feed_recent_days` (recent by END, like horaro.net), URL =
`page#ref`. `run_check` then does what it does for every source: adopt, `fresh()` (never twice by `source_ref`,
never a removed one), and **`add_candidate`** / suggest. Failures go through `check_failed` (`checks_failed`,
`marathon.feed_failed`, the third is `marathon.feed_stale`), said in words.

**Name**: the show as the sheet writes it (*GDQueer*). **Month + year are added** (*GDQueer (Oct 2026)*) only when the
sheet holds two blocks of that show at once, or a marathon of that source already has the plain name (live or
archived) — so a second GDQueer in March does not share a name with October's.

**The schedule**: the marathon's URL is `https://gamesdonequick.com/hotfix/schedule#gdqueer/2026-10-03`; `read_url`
learns it, and every schedule refresh re-reads the sheet through `ScheduleClient.runs`, so a moved run or changed
estimate flows through the existing diff (`Marathons.apply`) like any other source (proven:
`test_a_moved_run_in_the_sheet_flows_through_the_schedule_read`).

**The show list** — `marathon_hotfix_shows` (text, default `GDQueer`, Marathons group): one to 20 names, each at
most 60 characters, separated by commas; `checked_shows` trims, collapses spaces and keeps each show once whatever
its capitals; blank is refused in words (*… To stop the Hotfix feed, pause it instead.*). Doors: the **Settings
page** and the `/settings` panel's key card (registry), the **Hotfix feed's drawer** on Events ▸ Sources (a *Shows*
field that saves through `PUT /api/settings/marathon_hotfix_shows` — the one writer — and a link to the sheet it
reads), and the Discord feed card shows *Shows: …* with where to change it. Mock row, label, help and the mock
checker are mirrored.

**Seed**: `Seed("gamesdonequick", "gdq_hotfix", <page>, "GDQ Hotfix")`, appended to `SEEDS`. ⚠️ **Conductor's
assumption, recorded:** Hotfix airs on GDQ's own channel, so the feed sits on the `gamesdonequick` row; staff can
**Move to channel…**. Two changes make that possible:

1. ⚠️ **One feed per SOURCE on a channel, not one feed per channel** (schema **80**): the index
   `marathon_feeds_one_per_channel (guild_id, spotlight_id)` is retired (`RETIRED_INDEXES`) and
   `marathon_feeds_one_per_channel_source (guild_id, spotlight_id, source)` replaces it. The GDQ row keeps its
   `tracker` feed and takes the `gdq_hotfix` feed beside it. `feed_by_channel` now takes the source; the refusal
   reads *… already has a feed that reads {source}, **{name}** … A channel has one feed per source — remove that one
   first.*; opting a channel out holds EVERY feed on it, removing a channel row removes every feed on it, **Add a
   feed…** offers every channel that takes marathons, **Move to channel…** offers channels without a feed of that
   source. This REVERSES `marathon-feeds-design.md` Deviation 5 (edited there, checklist 35).
2. **Seed markers per seed**: `marathon_feed_seeds` marked the LOGIN once ever, and `gamesdonequick` is marked live,
   so a new seed on that login would never run. `mf.seed_marker`: a login's FIRST seed still marks the bare login
   (every marker written so far), a later one marks `login/source` (`gamesdonequick/gdq_hotfix`). The seed also
   checks for a feed of ITS source on the row, not "any feed". No schema change for the markers.

So **the first boot after deploy seeds *GDQ Hotfix* on the GDQ row and its first check adds GDQueer** (with
`marathon_feed_action_default` = `add`; `suggest` posts the Add it / Not this one notice instead). A staff-removed
Hotfix feed is not re-seeded.

**Nothing pings** (owner: no pings for now): the build turns no ping key on; a Hotfix marathon gets exactly what any
feed-found marathon gets from the existing settings (`marathon_feed_notice_when`, the inbox, auto-track off by
default). Spotlight rules unchanged.

## Deviations

1. ⚠️ **The ref is `gdqueer/2026-10-03`, not the brief's `gdqueer:2026-10-03`.** A feed notice's buttons carry the
   ref in a custom id that accepts only `A-Za-z0-9_./-` (`buttonable`); a colon would post suggest-mode notices with
   no buttons. `/` is the horaro.net precedent. Spaces in a show become `-` for the same reason.
2. ⚠️ **One feed per source per channel** (above) — the brief assumed only `UNIQUE (guild_id, source, feed_ref)`;
   the one-per-channel index would have refused the seed outright.
3. **Seed marker per seed** (above) — without it the seed would never run on the live GDQ row.
4. **A day's start is the first parseable *Show Start* of that show on that date**; later rows' start cells are
   ignored even if they differ (the owner's 14:2x clarification). A row with a blank start takes the day's.
5. **A block the sheet stops listing reads as unpublished**, not as a failure (above).
6. **Hosts are read** (a `host` person) when the host is not the show itself — the brief listed runners only. Fast
   Travel's *NickRPGreen*, Special Event's *ChurchnSarge* would match a BaF member by the Discord-username rule.
7. **A bare page link** (`…/hotfix/schedule`) is refused at Add with words asking for `#<show>`; `#<show>` alone
   resolves to that show's next block. ⚠️ `schedule_url` is UNIQUE per server, so a staff Add of `#GDQueer` for a
   LATER block, while an earlier one pasted the same way is on the list, is refused as already added — paste
   `#gdqueer/<date>` instead. The feed's own adds always carry the date.
8. **The client's memory of the last good CSV URL** serves schedule refreshes (which have no feed row); the feed's
   column serves checks. Both are the same allowlisted URL.
9. **`doc_import.hop_allowed` gained `hosts`/`tails` and `aiohttp_hop` an `agent`** (defaults unchanged; the Doc
   import's seven-target SSRF test still passes untouched) — reuse rather than a second guard.
10. **The mock** has feed **40** *GDQ Hotfix* on channel row 1 and marathon **50** *GDQueer* (id 40 is the mock's
    archived SGDQ 2026, which `check.mjs` reads); it mirrors the per-source refusal and, new, the one-feed-per-ref
    refusal (`duplicate_feed`) for every kind. The mock's `feedCheck` still acts on the GDQ feed only.
11. **`marathon_unknown_site`'s default names *the GDQ Hotfix schedule*** (a staff override is kept).
12. **`ruff format`** was run on the two new files only; touched shared files were not reformatted (the precedent).

## Tests

`tests/test_marathon_hotfix.py` (new, 35): the block (dates, 24 runs, 13 + 11), the clock (1:08 after 1 PM, then
+2:00, day two restarts at 1 PM, the last run 01:39Z–03:09Z, runs back to back), DST, runners and logins, hosts, a
second block weeks later, show matching, column refusal, the show list, `read_ref` forms, `block_for`, candidates and
names, `sheet_url_of`, the walk (page → CSV, a googleusercontent redirect followed), **the SSRF guard — eight
redirect targets (`evil.example`, a look-alike docs host, plain `http`, a look-alike content host, port 8443, the
`169.254.169.254` metadata address, `drive.google.com`, userinfo) each refused with the fake transport asked for
only the page and the CSV**, no sheet, the fallback (and an off-list fallback never fetched), too big / unreachable
/ not a sheet, the client's resolve + runs + memory, both line endings. `tests/test_marathon_sources.py` +1,
`tests/test_marathon_feeds.py` (the seed list), `tests/cogs/content/test_marathon_feeds.py` +6 (the seed beside a
pre-marked GDQ row and not again after a Remove; a check adds GDQueer once with its 24 runs and remembers the sheet;
the shows setting decides; a moved run flows through a schedule read; no sheet is a failed check in words; Add a
feed ▸ gdq_hotfix beside the tracker feed and never two) and five changed for one-feed-per-source,
`tests/api/tools/test_marathon_feeds.py` (the refusal's words), `tests/storage/test_db.py` +1 (a schema-79 file
with the old index and a tracker feed: the index is swapped, `sheet_url` added, a Hotfix feed fits beside the
tracker, a second tracker does not) and the per-source constraint test, `tests/test_settings_store.py` +1 (the key).
No test makes a network call.

## What was NOT verified

1. ⚠️ **No live fetch from this build.** The reader is proven on the two files the conductor captured; the bot's
   aiohttp client has not read gamesdonequick.com or docs.google.com, and **not from Fly**. If GDQ's host refuses
   `BROWSER_AGENT` or a datacenter address, the first check fails in words (`checks_failed`).
2. **Whether Google answers `pub?…output=csv` directly or via a `*.googleusercontent.com` redirect** today — both
   are allowed; the redirect path is proven only on a fake.
3. **Nothing met Discord.** The seed, the add, the notice/inbox and the drawer's Shows field ran against the suite's
   fakes and the mock (`check.mjs` ok; the field itself was not clicked in a browser — no browser use in this build).
4. **Schema 80** was proven on a fresh file and on a downgraded 79 file, not on the live volume.
5. **Live check after deploy** (the owner's): the first boot logs `marathon.feed_seeded` with *GDQ Hotfix*; its
   first check (`marathon.feed_checked` *GDQ Hotfix* found ≥ 1) adds **GDQueer** with **24 runs**, the first
   **Sat 2026-10-03 10:00 Phoenix** (17:00Z), the last **Sun 2026-10-04 18:39 Phoenix** (01:39Z Mon), ending 20:09
   Phoenix. The feed drawer shows *Shows: GDQueer* and the sheet link. Sweeps `HF-a…d`.


## Show picker and runner/host tracker (branch `hotfix-picker`, 2026-09-28)

> 🔨 **BUILT on branch `hotfix-picker`** (off `main` `9e708194`; commits `cf6dd819` route + tracker + keys + tests,
> `2fc24074` drawer + mock + contract, and the docs commit) — **NOT merged, NOT deployed, nothing has met Discord or
> Fly, no live fetch.** Schema **80** unchanged; registry keys **695 → 699**; routes **+1** (`check.mjs`: *22 pages,
> 283 routes*). **Last verified: 2026-09-28** against the conductor's fixture `gdq_hotfix_sheet.csv` only.

**The ask, verbatim** (owner, 2026-09-28 14:5x): *"can we also have a section where hotfix schedule loads and we can
manually enter or check which shows off a list that we want to track? Also lets do runner trackers. It looks like
Anarchy is in the host category, thats a BaF member so lets track that too"* — narrowed 15:0x: *"make it optional to
scan and spotlight for. that way we do runners scanned and shown by default ... for host we can choose to check for
host"*.

### As built

- **Route** `GET /api/marathons/feeds/{id}/hotfix-shows` (staff; the feeds router's gate). The shared function is
  `cogs/content/marathon_feeds.py:hotfix_picker`. It reads the sheet through the feed's own guarded reader
  (`client.hotfix_sheet(feed_ref, feed.sheet_url)` — the same page → CSV walk, allowlist, caps and last-good-URL
  fallback) and keeps a **five-minute in-memory copy** on the cog (`marathon_hotfix.SheetCache`, `cache_of(cog)`,
  `CACHE_SECONDS = 300`). Every feed check refreshes that copy too. While the copy is fresh, opening the drawer asks
  GDQ nothing. When a read fails and a copy exists, the answer is that copy with `stale: true` and `trouble` (the
  reason in words). With no copy it is **502 `unreadable`**: *The GDQ Hotfix schedule could not be read just now
  (…), and there is no earlier copy to show.* A feed that is not the Hotfix feed is **409 `not_hotfix`**. The GET
  writes nothing (the feed's `sheet_url` is written only by checks).
- **Answer**: `feed_id, shows, missing` (listed names the sheet does not hold), `track_people, timezone, sheet_url,
  read_at, stale, trouble, blocks[]`. Each block has `ref, show, key, first, last, starts_at, ends_at, starts_local`
  (the guild's `default_timezone`, `Fri 2 Oct 16:00`), `days[]` (`date, starts_at, starts_local` for each show-day),
  `hosts, runs, listed, tracked` and `because[]`: `{kind: listed}` and/or `{kind: runs|hosts, name, user_id}` (the id
  is a string, so JavaScript does not round it).
- **The drawer** (`marathons-section.js:hotfixFields` → `hotfixPicker`): the *Shows* field loads the route and draws
  one row per show, grouped by show name. Each row has a tick (= listed), the show-days as date chips (lit ✦ when a
  BaF person is on it; the chip's title gives the run count and host), *hosted by …*, and why:
  *tracked — on the list* / *tracked because anarchy hosts* / *not tracked*. **Add** takes a typed show name. A
  name the sheet already holds ticks its row; a name it does not hold becomes a row *listed, not on the sheet this
  week · Remove*. Listed names the sheet no longer holds get the same **Remove**. **Save the shows** (enabled once
  something changed) writes `marathon_hotfix_shows` through `saveSetting` — the settings route, the one writer — and
  the settings validator's refusals (blank, more than 20, over 60 characters) come back in words. The search box is
  the shared `listFilter` (owner rule: one search module); it appears above eight shows. A failed load draws
  `sentenceFor(error)`, so an outage reads as an outage and a 403 as access. The two lines of chrome (the tracker
  on/off note and the stale note) are page constants, the staff-chrome convention.
- **The tracker** — `marathon_hotfix_track_people` (bool, **on**). When it is on, a check takes every block a listed
  show owns **plus** every block a BaF person is on (`marathon_hotfix.tracked`), each with its reasons. People are
  matched by `marathon.match_people`, the People card's rule (**one rule, not a new one**), against the **everywhere**
  pairings only (`marathon_id IS NULL`; a pairing made for one marathon never tracks a show), the members' Twitch
  links (`golive_links`) and the exact Discord-username rule for a name with no Twitch link.
  **A block that is listed and has a person on it is one candidate with both reasons.** It is still one marathon,
  never two, because it has one ref (`fresh()` never takes a ref twice).
- **Hosts** — `marathon_scan_hosts_default` (bool, **OFF**; owner narrowing 15:0x). `match_people` gained
  `scan_hosts`, so a `host` part is matched only while BOTH `marathon_match_hosts` and this key are on. Commentators
  still follow `marathon_match_hosts` alone. This one key decides two things. First, whether hosts count toward
  tracking a Hotfix block (feed check and picker). Second, whether hosts show ✦BaF on EVERY marathon: `rematch`
  passes it, and the mock's `marathonRematch` mirrors it. Hotfix hosts were already read as `host` people by
  `marathon-hotfix` (Deviation 6), so a Hotfix marathon's People card lists its host, ✦BaF when paired AND scanned.
  ~~No per-marathon toggle, no host spotlight, no host events — those are the follow-up build's.~~ ➕ **2026-09-28,
  branch `marathon-host-spotlight` (🔨 BUILT, NOT MERGED):** built — `marathons.scan_hosts` per marathon (NULL follows
  this key; `rematch` reads it), Spotlight… for a host with its own note, and BaF host events
  (`marathons.host_events`, `marathon_host_events_default`, off). The Hotfix picker and feed tracker still read this
  global key — a show block has no marathon row to ask. [`marathon-host-spotlight-design.md`](marathon-host-spotlight-design.md).
- **The notice** — the feed notice words are keys, so the reason lines are two keys:
  `marathon_hotfix_hosts_template` (*Tracked because **{people}** hosts it.*) and `marathon_hotfix_runs_template`
  (*Tracked because **{people}** runs in it.*), fields `{people} {show}`. They are appended on a new line to the
  suggest notice (from the candidate) and to the inbox line of an added Hotfix marathon (re-derived at render from
  its stored runs' matched people, `marathon_because`). They appear **only when the show is not listed** — a listed
  show needs no explanation. `marathon.feed_added` / `feed_suggested` / `would_*` rows carry
  `because: {hosts: "anarchy"}` / `{runs: "…"}` the same way.

### Deviations

1. ⚠️ **The fixture holds 11 show blocks, not the brief's 13 blocks / 12 shows.** There are 14 show-DAYS and 11
   shows. Special Event (9/25–9/27) and GDQueer (10/3–10/4) are each ONE block under the existing grouping (a gap of
   more than a day starts a new block), and the feed makes one marathon per block. The picker keeps that unit and
   shows each block's days as chips, so all 14 show-days are visible (`days[]`, new `Block.days`).
2. ⚠️ **`The_Mathcat` is NOT matched by an everywhere pairing named `mathcat`.** The existing rule compares pairing
   names exactly (case- and space-folded, `runner_key`), and the brief said not to invent a fuzzy one. GDQueer
   tracks for Mathcat when their Go-live Twitch link is `the_mathcat` (the sheet links `twitch.tv/The_Mathcat`) or
   when a pairing names `The_Mathcat`. The People card's near-miss rule may OFFER the link (*looks like @…*); it does
   not make it. Tested both ways.
3. ⚠️ **Hosts behind `marathon_scan_hosts_default` (default off) is a behaviour change for EVERY marathon.** A GDQ
   host who showed ✦BaF through a pairing or a Twitch link stops counting at the next rematch, until staff turn the
   key on. Commentators are unaffected. Four existing tests that relied on a host matching now turn the key on first.
4. **Anarchy is NOT tracked by default**: Hidden Heroes is tracked because anarchy hosts it only after BOTH (a) the
   conductor pairs `anarchy` → `anarchyasf` for every schedule and (b) `marathon_scan_hosts_default` is turned on.
   With the key off the picker shows *hosted by anarchy · not tracked*.
5. **The near-miss posts** (`marathon_near_miss`) still consider hosts under `marathon_match_hosts` alone — not
   touched (out of scope). With host scanning off, a host-only near miss can still be posted, and linking it has no
   effect until scanning is on.
6. **The mock's sample** is the real 2026-09-28 sheet reduced to runners and hosts, with **Casey** (`caseyfast`, a
   linked mock member) added to GDQueer so the mock shows a person reason. The mock's feed check still acts on the
   GDQ feed only.
7. The first commit's test run had `labels.js` unstaged (the label test reads it). Each commit's suite was green in
   the tree it was run in; `cf6dd819` alone lacks the three labels, and `2fc24074` completes it.

### What was NOT verified

1. **No live fetch** — the picker reads through the same reader `marathon-hotfix` built, which is itself unproven
   against gamesdonequick.com / docs.google.com from Fly (see above).
2. **The drawer was never rendered or clicked** — no browser use in this build. `node --input-type=module --check`
   parses it, and `check.mjs` proves the route's shape against the mock. Ticking, Add, Remove, Save, the search box
   and the stale line have not been seen by anyone.
3. **Nothing met Discord**: the reason lines were checked against the suite's fake inbox and notice only.
4. **The `rematch` change on live data** — which live marathons have BaF hosts today (and so lose ✦BaF at the next
   read with scanning off) was not measured.

### Live check after merge + deploy (the owner's; sweeps `HF-e…HF-i`)

1. Events ▸ Sources… ▸ **GDQ Hotfix** ▸ *Shows*: 11 rows, GDQueer ticked, *hosted by anarchy* on Hidden Heroes (Fri 2
   Oct 16:00 Phoenix), *not tracked*.
2. Pair `anarchy` → @anarchyasf for every schedule, turn `marathon_scan_hosts_default` on, reopen the drawer: Hidden
   Heroes reads *tracked because anarchy hosts*; **Check now** adds it; the inbox line ends *Tracked because
   **anarchy** hosts it.*

## Follow-up 2026-10-03 — setup buffer (branch `hotfix-setup-buffer`)

> 🔨 **BUILT on branch `hotfix-setup-buffer`** (off `main` `aeca20b6`) — **NOT merged, NOT deployed, nothing has met
> Discord, Fly or a browser.** Schema unchanged; registry keys **706 → 707**; routes unchanged (`check.mjs`: *22
> pages, 288 routes*). **Last verified: 2026-10-03** against the fixture `gdq_hotfix_sheet.csv` and the suite only.

**The ask, verbatim** (owner, Sat 2026-10-03 20:0x Phoenix): *"for our hotfix schedule we should try and add a 5 - 10
min buffer beteen each run if there isnt already one built in the start times on this new sched or when predicting
using the old sched."*

**Why.** The Hotfix sheet gives one show start per day and an estimate per run; the bot stacked the estimates with
nothing between them, in two places — when the sheet is read (`marathon_hotfix._runs`) and when a run seen starting on
the stream re-times the later ones (`marathon_signals.retimed`). Real shows set up between runs. Measured from the
bot's own log on GDQueer day one, Sat 2026-10-03 (the conductor, `docs/TODO.md` chunk 2): the gap between a run's
estimated end and the next run's real start, 11 runs — **−4, +13, +6, +10, +8, +6, +9, +6, +7, +6, +7 minutes; median
7, mean 6.7**. Every prediction was early by about that much, and a sheet-only prediction drifts by the sum (JR's
Denshattack!: predicted 12:50 Phoenix, really live 13:21:57).

**The key.** `marathon_setup_minutes` — int, **default 7, bounds 0–30**, namespace `marathon`
(`settings_store.MARATHON_SETUP_MINUTES_KEY`; the max is `MARATHON_SETUP_MAX`). Settings ▸ Marathons on the site
(label *Setup minutes between runs when a schedule gives no start time per run*) and the `/settings` panel's key
card, both from the registry. **0 is the old stack of estimates exactly.**

**As built.**

- **The sheet read.** `marathon_hotfix._runs(rows, setup_minutes)`: the first run of a show-day starts at the show
  start; run N starts at run N−1's start + its estimate + the buffer. A run's `ends_at` is still start + estimate
  (the buffer is between runs, never inside one). `blocks_of(text, setup_minutes=0)` and
  `parse_hotfix(text, shows, setup_minutes=0)` carry it; `ScheduleClient.runs` / `.resolve` / `.hotfix_block` take
  `setup_minutes` and use it only on the Hotfix branch. On the fixture at 7: Hamtaro 18:15Z (was 18:08Z), day one
  ends 04:10Z (was 02:46Z), day two still starts 17:00Z, the block ends **2026-10-05 04:19Z** (was 03:09Z).
- **The re-time.** `marathon_signals.retimed(rows, setup_minutes=0)`: the run seen starting keeps its real start;
  each later run of its chain starts at the previous run's start + estimate (or its real end, when staff ended it) +
  the buffer.
- **Only where Black Bloc keeps the clock.** The cog asks through `cogs/content/marathon_signals.setup_for(bot,
  guild_id, source)`, which answers `{}` for every source whose `RETIMES_ITSELF` is `True` (GDQ tracker, RPGLB,
  horaro, Oengus, Fastest Furs, Lady Arcaders) — those readers are called with exactly the arguments they were
  called with before, and `retime` still returns at once for them.
- **The window follows.** `Block.ends_at` is the latest run end, so a Hotfix candidate's end, the picker's
  `ends_at`, and the marathon's own `ends_at` (`mt.span(runs)` in `Marathons.apply`) all move with the buffer —
  nothing computes a Hotfix end any other way.
- **Chains.** A chain was *next sheet start = previous sheet end ± 1 min*. It is now *0 to `MARATHON_SETUP_MAX`
  minutes after* (± 1 min) — see Deviation 1.

**When a changed value takes effect.**

| What | When |
|---|---|
| Upcoming runs' sheet times (and so their predicted starts, reminders, the board) | The next schedule read of that marathon: every `marathon_poll_minutes` (30 by default) while it is near, or at once with the drawer's refresh. The changed starts change the schedule hash, so the read is applied as a move; a run that shifts by `marathon_move_minutes` or more is logged `marathon.member_run_moved` (BaF runs) and has its reminder marks re-armed. |
| Runs after one seen starting on the stream | The next re-time, whichever comes first: the next run confirmed live by title or category, a staff move that marks a run live, done or not live, or the schedule read above. It does not wait for the read. |
| A run that is **live or done** | Never — see Deviation 2. Its `sheet_at` follows the sheet; its shown time does not move. |
| Suggestions in the inbox, the Hotfix show picker | The next feed check / the next time the drawer opens (the picker's 5-minute cache holds the sheet's TEXT, not its times). |
| A marathon's `ends_at` | The same schedule read. |

**Deviations**

1. **A chain is detected by a gap of 0–30 minutes, not by the exact buffer.** The brief asked for the buffer to be a
   parameter of the pure helpers; `retimed` takes it, `chains` deliberately does not. Between the moment the key
   changes and the next schedule read, the stored sheet times still carry the OLD buffer; matching on the new value
   would break every chain for up to half an hour and send the re-timed runs back to the sheet. Matching on the
   allowed range is right whatever the key says, and a show-day gap is many hours. At buffer 0 on a Hotfix sheet
   (gaps are exactly 0) this is the old result; a hand-built sheet with a 1–31 minute gap would now chain where it
   did not — no source produces one.
2. **A live or done run of a clock-kept schedule is not moved by a read** — two small rules, both new and both in
   force at buffer 0 too: (a) `Marathons._write_plan` leaves such a row's `scheduled_at`/`ends_at` alone and never
   flags it moved (`cogs/content/marathon_signals.holds` / `held_plan`; `sheet_at`/`sheet_ends_at` still follow the
   sheet so the chain stays measurable); (b) `retimed` leaves a live/done run that was never seen starting where it
   is stored (`settled`), using its stored end as the next run's base. Without them, the first read after the
   deploy (0 → 7) would have shifted finished GDQueer runs by up to 84 minutes and logged a
   `marathon.member_run_moved` for each BaF one. What changes at 0: a sheet edit no longer moves a run already live
   or done. Sources that re-time themselves are untouched by both.
3. **`resolve` takes the buffer as well as `runs`** — a bare show name picks the first block *not over yet*, and
   *over* is the block's end, which the buffer moves.
4. **Existing cog tests keep their old times by setting the key to 0** (`tests/cogs/content/test_marathon_signals.py`'s
   `gdqueer(bot, cog, setup=0)`), which is the *0 = the old behaviour* proof at cog level; two feed tests that run
   on the default moved 18:08Z → 18:15Z and 18:38Z → 18:45Z.
5. **After a real end the buffer is still added.** The brief's formula is start + estimate + buffer; when staff
   ended a run (`actual_ended_at`), the next run is that real end + buffer — the setup still has to happen.

**Tests** — `tests/test_marathon_hotfix.py` (0 = the bare stack exactly; 7 on the GDQueer fixture = start + estimates
+ 7×(n−1) for every run of both days; the block and candidate end follow; the client passes it),
`tests/test_marathon_signals.py` (0 exact; +7 after the anchor; earlier/live/done runs left alone; held runs; chains
across 0/7/30 under a different key), `tests/cogs/content/test_marathon_signals.py` (asked only for Hotfix, and a GDQ
marathon is read and timed exactly as before with the key at 30; a live confirm at 7; a changed key at the next
re-time; a changed key at the next read with live/done runs unmoved and the marathon's end following),
`tests/test_settings_store.py` (type, namespace, default, bounds, count 707).

**What was NOT verified**

1. **No browser** — the Settings row was read from the mock's `/api/settings` and written through its `PUT`
   (0 accepted, 31 refused in words); nobody has seen it rendered.
2. **Nothing met Discord, Fly, gamesdonequick.com or Twitch.** The `/settings` panel's card for the key was not
   opened; it comes from the registry like every other int key.
3. **7 is one day's median (11 runs, one show).** Whether it fits GDQueer day two, or the weekly Hotfix shows, is
   unmeasured — that is what the key is for.
4. **The live marathons' first read after deploy** — which upcoming BaF runs log a move — was not rehearsed against
   production data.

## Follow-up 2026-10-04 — a renamed run keeps its identity (branch `run-identity`)

> 🔨 **BUILT on branch `run-identity`** (off `main` `c31878a5`) — **NOT merged, NOT deployed, nothing has met
> Discord, Fly or a browser.** Schema unchanged; registry keys unchanged (**737**); routes unchanged (`check.mjs`:
> *23 pages, 291 routes*). One new log kind, `marathon.run_renamed`. **Last verified: 2026-10-04** against the
> suite and the fixture `gdq_hotfix_sheet.csv` (which still carries the typo) only.

**The incident** (measured by the conductor through the operator token; `docs/TODO.md` ▸ 🪪). At 2026-10-05
03:43:04Z GDQ's sheet changed Metroid Dread's category from *Minim Items Glitchless* to *Minimum Items Glitchless*.
A Hotfix run's `external_id` is the slug of its game and category (`marathon_hotfix._runs`), so the read answered
`added=1 dropped=1`: run 163, LIVE since 03:19Z with a BaF host's highlight up and both heads-ups posted, was
DROPPED, and run 176 was inserted and went live at 03:43Z. Members saw the highlight edited to its finished
wording mid-run, a second highlight, and both heads-ups reworded to *off the schedule*.

**What was changed, and what was not.** How `external_id` is derived is untouched (a function that produces a
persisted key is a migration). The change is in the one place a read reconciles stored rows with fresh runs,
`marathon.diff`: before a row is dropped and a run inserted, `marathon.renames` pairs them.

**The pairing rule** (`marathon.same_slot`) — a stored row that the read no longer names and a fresh run whose id
no live row holds are the same run when ALL of:

1. **The slot.** Either the planned starts (`sheet_at`, else `scheduled_at`, against the fresh `starts_at`) are
   under `marathon_move_minutes` apart (5 by default, never under 1), or the two have the same `order` and their
   planned starts are under 12 hours apart (`SAME_DAY_HOURS`). With no time on either side, the order alone.
2. **The runners.** The set of RUNNER names, normalised by `runner_key` (case and spacing), is equal. Hosts and
   commentators take no part: the organisers' overlay changes them without the run changing.
3. **No runners on either side** counts only when the game titles are alike: equal after `normalise`, or a
   `difflib` ratio of 0.8 or more (`SAME_TITLE`). Two blank titles are not alike.

**The tolerance is `marathon_move_minutes`**, not a new key: that key already holds the decision *how far may a
planned start differ and still be the same time* — below it a start has not moved. A typo fix moves nothing; the
overlay and the setup buffer shift by seconds or not at all. The order rule covers the read where the clock
differs by more (the overlay unreadable on that read, a day's start edited in the same save).

**Ambiguity pairs nothing** (`_only_pairs`). Every row is tested against every candidate run; a row is paired only
when exactly one run fits it AND that run fits no other row. A row fitting two runs, or two rows fitting one run,
stay a drop and an add — and do not stop a clear pair elsewhere in the same read.

**Kept by a renamed run:** its row — id, state (upcoming / live / done), `live_at`, `live_because`,
`actual_started_at`, `actual_ended_at`, `done_at`, `reminders_sent`, `reminder_posts`, the shout ids, `first_seen_at`,
and each person's match where name and part are unchanged (`_merged_people`). The host-block records on the
marathon are keyed by run id and so still fit. **Taken from the fresh run:** `external_id`, order, game, display
name, category, estimate, people, sheet times — the ordinary update, so a renamed run whose start also moved by the
threshold is a move as well.

**What follows.** One `marathon.run_renamed` row per pair (`run_id`, `from_id`, `to_id`, `game`, `category`,
`was_game`, `was_category`); `marathon.schedule_changed` and `marathon.fetched` carry `renamed` beside `added` /
`moved` / `dropped`, and a read that only renames still logs `schedule_changed`. Nothing is posted and nothing
pings. The existing syncs pick up the words: the board and runner post, a posted highlight (edited in place), and
the heads-ups of a run or block still UPCOMING. A heads-up for a block already live is not reworded — the existing
reminder sync follows upcoming and dropped blocks only, and no new editor was built.

**The repeat counter.** `_runs` names a second identical game/category `…#2`. Fix a typo on the FIRST of two and
the read names the fixed one freshly and calls the second by the first's old id, so id matching would move row 1
onto slot 2 and drop row 2. `renames` therefore looks once more when a lost row is still unpaired: id matches of
the same family (the id without `#n`) that put a row out of its slot are released and everything is paired by
slot again. The wider answer is taken only if every released row and run is paired and every first-pass pair
stands; otherwise the first pass is the answer.

**Flip-back.** (a) The sheet goes back to the old spelling after this build renamed the row: the row is lost
under the new id and found under the old one — renamed again, same row. (b) The old id is held by a DROPPED row
(the incident's shape: 163 dropped holding the old id, 176 live holding the new one): the fresh run's id match is
a dropped row, so it is a candidate for the live row; the live row takes the id and the dropped row takes the id
the live row gave up (`marathon.rekeys`) and stays dropped. `rekey_runs` writes every id change in one commit,
parking each row on `~rekey~<id>` first, so `UNIQUE (marathon_id, external_id)` never trips; a failure rolls
all of it back. The rekey and the field update are two commits; a stop between them leaves the row under its new
id with its old words, and the next read (the stored hash is written last) finishes it as an ordinary update, without
a `run_renamed` row.

**A DROPPED row that comes back under its OLD id** is unchanged: it is updated from the fresh run and goes back to
UPCOMING (`plan.reappeared`). The one exception is (b) above — when a live, upcoming or done row in the same slot
would be lost in that same read, that row is kept and the dropped row stays dropped.

**The incident's rows (163, 176) were not repaired**; that show is over.

**Deviations**

1. **No new settings key.** The brief allowed one if the tolerance was a real decision; `marathon_move_minutes` is
   that decision already, reachable both ways.
2. **"The same show-day block" is 12 hours, not a calendar day.** A stored run carries no day, and only Hotfix has
   an Eastern show-day (`marathon_overlay.show_day`, which `marathon.py` cannot import). It guards only the order
   rule; the time rule is far tighter.
3. **DONE rows are paired too.** Before this build a DONE row missing from a read was left as history and its new
   spelling inserted as a second, upcoming run; a renamed done run now keeps its one row.
4. **`marathon_overlay.kept` was touched** (outside the reconcile step). On a read where the organisers' sheet
   cannot be had, `kept` copies hosts, commentators and times from the stored row by `external_id`; a renamed run
   was unknown to it and would have lost its BaF host on exactly the incident's read. It now also looks the row up
   through `renames` when `laid` passes the tolerance (`minutes=None` is the old behaviour).
5. **The repeat-counter release** (above) goes beyond the brief's pairing of drops with adds; it is all-or-nothing
   and limited to one id family.
6. **A live block's posted heads-ups keep the old spelling** (see *What follows*).
7. **`schedule_changed` in the tracker's Moves list** says `, N renamed` only when N is not 0, so older rows read
   as they did; `run_renamed` has its own line.

**Tests** — `tests/test_marathon.py` (the slot's two rules and their edges, runners / hosts, the title rule, both
ambiguities, a swap, two renames, rename + add, done, dropped never renamed, the flip-back swap, two and three
repeats, a repeat removed beside an add), `tests/cogs/content/test_marathon.py` (upcoming with marks kept, live
with its real start, done, a title change, another runner, rename + add, a swap, a tracker id, repeats, both
flip-backs against the real `UNIQUE` index, a failed rekey rolled back), `tests/cogs/content/test_marathon_host_highlights.py`
(the incident with a posted highlight and two heads-ups: nothing sent, nothing reworded as dropped, the highlight
edited in place; an upcoming hosted run's heads-up reworded and its 15-minute mark still due once),
`tests/cogs/content/test_marathon_viewer.py` (the GDQueer fixture's own row, with the organisers' sheet, without
it, and with it unreadable), `tests/test_marathon_overlay.py` (`kept` with and without the tolerance),
`tests/test_marathon_schedule_page.py` (the Moves words).

**What was NOT verified**

1. **Nothing met Discord, Fly, the live sheet or a browser.** The edits are fake-channel edits.
2. **The live database's rows** were not read; whether any other marathon holds a DROPPED twin of a live run is
   unmeasured.
3. **The Moves list was not looked at in a browser**; its words are tested as strings, and the mock has no
   renamed row to show.
4. **A rename on the same read as a large shift with a changed order** is not paired (neither slot rule holds) and
   stays a drop and an add, as before.
