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
  run starts where the previous one ended (its estimate). The next date restarts at its own show start. A day with
  no parseable start has runs with no times.
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
