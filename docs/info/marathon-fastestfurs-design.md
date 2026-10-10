# The Fastest Furs feed — a fifth marathon source, read off the org's own site

> ✅ **2026-09-26 13:4x — LIVE as v173 13:35** (merge `e29563c6` of `5de2323c`; release commit `5a66acd2` (`release.json` v173 at `aee13ffe`); ONE fast-forward of `main` to `merge-marathon-sources` `282ce0ee`; boot `database ready` 20:35:43Z, `synced 33 app commands` 20:35:43Z, `logged in as Black_Bloc` 20:35:46Z, no Traceback, `/health` 63 ms — `deploys.log`'s v173 line). **Live proof 13:36–13:37**: after the deploy the session added channel row **8 `fastestfurs`** (marathons ON, spotlight and announce OFF, `ping_mode` always) and feed **5 Fastest Furs** through the owner's browser session; its first check found 1 / added 1 → marathon **#7 *Fastest Furs Fall Fest 2026*** (ref 21, 2026-10-08 14:00Z, **55 runs**) → **two BaF runners matched** (run 36 Mathcat — *Dr. Robotnik's Ring Racers*; run 63 glitchaston — *Kirby's Blowout Blast*) → ping window 2 set 10-08 12:00Z → 10-12 04:41Z → staff notice posted `because=published home=shadow` (channel 1542316174472380517, message 1553505728373719063). So Fly reads `cheetah.fastestfurs.com` (no KI-30 wall). Not opened in Discord by hand; sweeps `FF-a…d` are the owner's. The status line below is history.

> **Audience:** the conductor, reviewers and future sessions touching marathon sources. **Status:** TRACKED ·
> 🔨 **BUILT on branch `marathon-fastestfurs`** (off `main` `a3ac5132`; commits `c6e7f2dc` code + tests + fixtures,
> `e34426d2` site + mock, and the docs commit) — **NOT merged, NOT deployed, nothing has met Discord or Fly.**
> **Last verified: 2026-09-26** (~13:xx Phoenix) — five live GETs from the build machine (`urllib`, a plain
> User-Agent, one read per URL): `cheetah.fastestfurs.com/api/events`, `/api/public/schedules/event/21`, `…/event/16`,
> `…/event/999`, and the page `fastestfurs.com/schedule/21`. **NOT checked:** the bot's own `ScheduleClient`
> (aiohttp, `BROWSER_AGENT`) against `cheetah.fastestfurs.com`; any read from Fly (KI-30's datacenter wall is untested
> on this host); a live event's `actualDuration`; the rendered schedule page itself (a script-rendered app). Secret
> NAMES only — there are none here. Research: [`marathon-orgs-research-2026-09-26.md`](marathon-orgs-research-2026-09-26.md)
> *Fastest Furs*. Template: [`marathon-feeds-design.md`](marathon-feeds-design.md) §H (the Oengus build).

## The ask, verbatim (owner, 2026-09-26 12:3x Phoenix)

*"Build them all now"* — after the orgs research; Fastest Furs is this branch (two sibling branches build the
other two orgs in parallel).

## What the API answers (measured 2026-09-26)

| Read | Answer |
|---|---|
| `GET https://cheetah.fastestfurs.com/api/events` | 200 `application/json`, a **bare JSON list** (not an object) of 17 events, newest first, each `{id, name, short, startDate, endDate, amountRaised, charityName, logoLink, playlistLink, submissionsOpen, isInPerson, createdAt, updatedAt, charityId, hideRunStatus, charities{…}, eventHosts[{host{id, name, pronouns}}]}`. Dates are **midnight UTC, date only** (`2026-10-08T00:00:00.000Z`); events before 2026 carry `endDate == startDate`. No `twitch` field. |
| `GET …/api/public/schedules/event/21` | 200, `{id 23, eventId 21, startDateTime "2026-10-08T14:00:00.000Z", timeZone "UTC", createdAt, updatedAt, events{…}, scheduleItems[65]}`; each item `{id, scheduleId, runId, itemType "run"/"break", duration, setupTime, actualDuration, orderIndex, label, runs, scheduleItemHosts[{host{id, name, pronouns}}]}` — `duration`/`setupTime` in **minutes**, **no per-item start time**. `runs` (null on a break) is `{id, name` (the game)`, category, console, estimatedTime "00:35:00", actualTime, runners` (**one plain string**, `"karma_dragoness, winnerbit"` for a race)`, pronouns, videoLink, status "Accepted", photosensitivityWarning, events{…}}`. 55 runs, 10 breaks, every run one host, `orderIndex` 0…64 already in order, `actualDuration` all null. |
| `GET …/event/16` (Fall Fest 2025) | 200, the same shape (`timeZone "America/New_York"`, `startDateTime` still an explicit `Z` time). |
| `GET …/event/999` | **404** `{"message": "Schedule not found for this event"}`. |
| `GET https://fastestfurs.com/schedule/21` | 200 `text/html`, the app shell (`<title>Fastest Furs Fall Fest 2026 - Fastest Furs</title>`) — the route exists; the page is script-rendered, so this proves the link lands on the site, not what it draws. |

**Fall Fest 2026 is on `/api/events` today: id `21`, short `FFFF26`, 2026-10-08 → 2026-10-11, schedule published
(65 items, first run 2026-10-08 14:00Z).**

## The design as built

**Source `fastestfurs`** (`marathon_sources.FASTESTFURS`, appended to `SOURCES`; not a tracker). `SOURCE_WORDS` →
*Fastest Furs*, `SITE_WORDS` / `site_of` → *fastestfurs.com*. `read_url` accepts `https://fastestfurs.com/schedule/<id>`
(and `www.`) and the API link `https://cheetah.fastestfurs.com/api/public/schedules/event/<id>`, both → ref `<id>`;
`schedule_page` → `https://fastestfurs.com/schedule/<id>`. Everything Fastest-Furs-specific lives in the new module
`black_bloc/marathon_fastestfurs.py`; the shared files carry one constant, one dict entry and one branch after the
Oengus branch in each dispatcher (`read_url`, `schedule_page`, `resolve`, `runs`), reaching the module through
`marathon_sources._ff()` (a function-level import — the module imports `Run`, `Person`, `ScheduleError` from
`marathon_sources`, so a top-level import either way would be a cycle).

**Reader.** `parse_fastestfurs(payload)` walks `scheduleItems` in `orderIndex` order from `startDateTime`: each item
starts where the one before ended, and lasts `duration` + `setupTime` minutes — **breaks advance the clock but are
not runs**. A run's `starts_at` is that running total, `ends_at` = start + `duration` + `setupTime` (the next item
starts there, as the tracker's `endtime` does), `run_seconds` = `duration`, `external_id` = the run's `id` (stable
across a rebuilt schedule; the item id is the fallback), `order` = `orderIndex + 1`. People: `runners` split with the
horaro.net `PLAYER_SPLIT` (`,` `&` `vs` `and`), each a name-only `Person(name, None, runner)`, then each
`scheduleItemHosts[].host.name` as `Person(name, None, host)` — never a login (the match falls to the Discord-username
step and staff pairings). `ScheduleClient.runs("fastestfurs", ref)` → `read_runs`: a **404** or a 200 with **no run
items** raises `ScheduleError("fastestfurs.com has the event but has not published its schedule yet",
unpublished=True)` — the Oengus/GDQ-404 path (runs kept, no failure counted, re-read on the far cadence).
`resolve` reads `/api/events` (one GET) for the name, so an event whose schedule is not out still resolves.

**Feed `fastestfurs`** (`marathon_feeds.FASTESTFURS_FEED`, appended to `FEED_SOURCES`). `feed_ref` = the channel's
login (the Oengus precedent, §H Deviation 3 — `UNIQUE (guild_id, source, feed_ref)` would otherwise allow one per
server); **Add a feed** and **Move to channel…** write it from the channel row. Each check is ONE GET of
`/api/events` (`ScheduleClient.fastestfurs_events`) and `candidates(events, now, recent_days)` yields a `Candidate`
per event whose end is ahead of now or within `marathon_feed_recent_days`: ref = the event id, name = the event's
`name`, `url` = `schedule_page`. **No per-event channel check**: the API is Fastest Furs' own, so every event on it
airs on their channel. The candidates go through the same `run_check` → `fresh` → `add_candidate` path as every
other feed, so the v171 rule holds (the marathon is added quietly; its staff notice posts once a read finds runs).
**No per-feed memory**: the dedupe is `marathons_by_ref` + `ignored`, exactly as a tracker feed; `seen` is unused
(so **Look again** is not offered on this feed — nothing to re-read).

**Seed** `Seed("fastestfurs", FASTESTFURS_FEED, "fastestfurs", "Fastest Furs")`, appended to `SEEDS`. Confirmed from
`cogs/content/marathon_feeds.py` `tick_feeds` / `seed_feeds`: the seed runs once per process per guild (the first
tick after boot, while `marathon_feeds` is on and `marathon_mode` is not off); for a login with **no channel row**
it `continue`s **before** `mark_seeded`, so no marker is written and the next boot tries again; once a row with
login `fastestfurs` exists (and takes marathons), the first boot after that makes the feed and writes the marker —
a feed staff remove later stays removed. **The seed fires on the first boot (deploy or restart) after the row is
added, not the moment it is added**; staff who want it sooner use **Add a feed… ▸ Fastest Furs**, and the next boot
then just writes the marker.

**Words and site.** Pick `fastestfurs` — *Fastest Furs — every event on the org's own list at fastestfurs.com*
(`PICK_WORDS`; the API's `sources` list carries it). The unknown-pick refusal and the Discord modal's field name it.
`marathon_unknown_site`'s default: *I can read the GDQ and RPG Limit Break trackers, horaro.net schedules, Oengus
marathons and Fastest Furs schedules — that link is none of them.* (a stored staff override is kept — only the
registry default and the mock row changed). Site: `PICK_HELP.fastestfurs` (*Every event on Fastest Furs' own list at
fastestfurs.com — nothing to type.*), `PICK_GUESS.fastestfurs`, the Add a feed note names it; the Source column word
comes from `SOURCE_WORDS` (*Fastest Furs*). Mock: channel row **31** `fastestfurs`, feed **31** (add mode), marathon
**31** *Fastest Furs Fall Fest 2026* with two name-only runs (one a race, both with a host); `marathonReadAny`,
`feedPick`, `feedSourceWord`, the create and move branches. `contract.json` unchanged — no enum there lists sources.

**Fixtures** (captured 2026-09-26, trimmed): `tests/fixtures/marathon/fastestfurs_events.json` (791 B — events 21, 19,
16 with `id, name, short, startDate, endDate, charityName, submissionsOpen, isInPerson`; hosts, logos and timestamps
dropped) and `fastestfurs_schedule_21.json` (4,549 B — Fall Fest 2026's first 9 items: 8 runs incl. the race
`Racin' Ratz` and 1 break, each host's `name` only, every `pronouns` field dropped).

## Deviations

1. **The events list is a bare JSON array**, which `ScheduleClient._json` refuses (it wants an object), so the reader
   takes the client's `_request` callable directly (`read_events(request)`), checks for a list itself and refuses
   anything else with the shared `NOT_JSON` words.
2. **Run times are computed, not read**: no item carries a start. Start = `startDateTime` + the running total of
   every earlier item's `duration + setupTime` (breaks included). Setup is taken to FOLLOW its run (first run starts
   at `startDateTime`); that reading matches the tracker and Oengus but was not confirmed against the rendered page.
3. **`run_seconds` = `duration`, not `estimatedTime`** — they differ on some runs (Islets: `duration` 87,
   `estimatedTime` 01:25:00); `duration` is what the timeline is built from.
4. ~~⚠️ **`actualDuration` is ignored.** It is null on every item today; during a live event it probably holds the
   real length and the site may re-time later runs. Not modelled (not measurable until 2026-10-08).~~ **Reversed
   2026-10-09 (`afc8af6d`):** it is the real length of every finished item and the walk now uses it; see
   *Actual durations (2026-10-09)* below. Why it flipped: Mathcat's run posted ~40 min late on the planned walk.
5. **Date-only event dates**: the list writes `startDate`/`endDate` as midnight UTC. A candidate's `starts_at` is moved
   to **12:00 UTC** of the first day (so a Discord `<t:…:D>` stamp reads the right calendar day either side of UTC,
   not *Oct 7* in Phoenix) and its end to the **midnight after the last day** — "recent" is measured from that end
   (an event counts through its last day, plus `marathon_feed_recent_days`). A stamp that is not exactly midnight is
   kept as given. The marathon row's own dates come from its runs on the first read with runs, as for every source.
6. **No schedule → unpublished, two ways**: a 404 (measured on a missing event) and a 200 with zero run items (the
   shape an event with a schedule row but no runs would answer — **not measured**; no such event exists today).
7. **External id = the run's id**, not the schedule item's — a schedule rebuilt from the same submissions keeps its
   run ids; the item id is only the fallback.
8. **`resolve` reads the events list** (not the schedule) for the name, so a staff-pasted link to an event whose
   schedule is not out is still added (and waits, unpublished).
9. **`_ff()` in `marathon_sources`**: the new module is reached through one function-level import (the cycle above).
   `_site_of_url` was NOT given a Fastest Furs entry: a transport failure says *cheetah.fastestfurs.com could not be
   reached*, the host from the URL, which is accurate.
10. **The Discord modal's source field**: `max_length` 10 → **20** (`fastestfurs` is 11 characters) and its label is now
    *Source: gdq/rpglb/horaro/oengus/fastestfurs* (43 characters — Discord caps a label at 45, so the old
    *Read from — gdq, rpglb, horaro or oengus* could not simply grow). **Superseded at the merge (2026-09-26):** with
    seven picks the label is *Source — a pick; clear the box to list all* and the list is the field's placeholder
    (`code-notes.md`, the marathon-source merges section).
11. **No new settings key.** Every new sentence (`PICK_WORDS`, the unpublished line, the site's pick help) is a panel
    or page constant beside its siblings, which the bot does not post; `marathon_unknown_site` changed default only.
    The help texts of `marathon_feeds` / `marathon_feed_recent_days` were NOT touched (they still list the older
    sources) — left for the conductor to word once all three sibling sources merge.
12. **Mock ids 31** for the channel row, the feed, the marathon and runs 31/32 — chosen far from the next free id so
    the two sibling branches' samples do not collide at merge. The mock's `feedCheck` still acts on the GDQ feed only,
    so **Check now** on the Fastest Furs row adds nothing in the mock.
13. **One old test was amended, not added to**: `test_the_seeds_are_the_two_tracker_channel_rows_and_ss4c_on_oengus_and_not_esa`
    now lists the Fastest Furs seed and reads SS4C by index 2; `tests/api/tools/test_marathon_feeds.py`'s sources list
    gains `fastestfurs`.
14. **`ruff format --check` fails on six touched files — and on the same six at `a3ac5132`** (`cogs/content/marathon_feeds.py`,
    `marathon_feeds.py`, `settings_store.py`, and three test files); none of the reformat hunks are lines this branch
    added. Whole files were NOT reformatted. `marathon_fastestfurs.py`, its test, `marathon_sources.py` and its test
    are clean; `ruff check .` is clean.
15. **Tests:** `tests/test_marathon_fastestfurs.py` (22 cases: read_url forms, page, the walk incl. the break, name-only
    runners + hosts, broken items, candidates incl. the last-day edge, the client: list / not a list / 503, the
    schedule, unpublished ×2, a 500 is not unpublished, resolve), `tests/test_marathon_sources.py` +2 functions (3
    cases), `tests/test_marathon_feeds.py` +1, `tests/cogs/content/test_marathon_feeds.py` +5 (seed once; the check adds
    Fall Fest quietly and skips 19/16; a second check adds nothing; the notice posts once when runs appear; Add a feed
    ▸ fastestfurs keys on the login and `guess_pick`).

## What was NOT verified

1. ⚠️ **Nothing met Discord or Fly.** The seed, the check, the quiet add and the published-notice ran only against the
   suite's fakes (`FeedClient.fastestfurs_events` returns the fixture).
2. ⚠️ **The bot's own `ScheduleClient` never read `cheetah.fastestfurs.com`** — the fixtures came from `urllib` on the
   build machine; the aiohttp path's `json(content_type=None)` on a list body is untested live. **Not from Fly.**
3. **The rendered schedule page** was not compared with the computed times (Deviation 2) — the app is script-rendered
   and was not opened in a browser.
4. **`actualDuration` / live re-timing** (Deviation 4) and a **zero-run schedule** (Deviation 6) were not observed.
5. **The live bot has NO `fastestfurs` channel row** (orgs research, 2026-09-26 12:1x); nothing here reads the live
   database. Until staff add it, the seed does nothing.
6. **Cost:** one `/api/events` GET per 6 h per feed (~39 KB today) plus the schedule reads any marathon costs; rate
   limits not measured.
7. **The page** was rendered in `chrome-headless-shell` 149.0.7827.22 over raw CDP against this branch's mock on
   `MOCK_PORT=8806`: the Sources drawer lists **Fastest Furs · Fastest Furs · every 6 h …**; **Add a feed…** offers
   the `fastestfurs` pick, shows its help line and hides the slug field; the Marathons list shows *Fastest Furs Fall
   Fest 2026 · Fastest Furs · feed · far off · 0 of 2*; its drawer opens (*2 runs · 0 BaF*). **Zero console errors.**
   Nothing was submitted in a browser; the Fastest Furs feed's own drawer was not opened (the click landed on the
   table cell). The writes were checked by `check.mjs` and the tests.

## Actual durations (2026-10-09)

> Branch `ff-actual-durations` (off `main` `01d6e72b`), code commit `afc8af6d`. **NOT merged, NOT deployed.**

**The report (owner, Fri 2026-10-09 ~3:3x PM Phoenix, verbatim):** *"Fastest fur Mathcat run seemed like it posted late"*, then *"It looks like the run has been on for an hour and 5 minutes according to on screen timer"*.
**The cadence decision (owner, same afternoon, verbatim):** *"Let's check every 30 minutes until an event starts then poll every minute during the event."*

**Measured.** Marathon #7 *Fastest Furs Fall Fest 2026* (feed 5, schedule 23, ref 21), run #36 external id 889
*Dr. Robotnik's Ring Racers* by Mathcat, `orderIndex` 23: the bot posted its 2 h reminder 20:20:59Z, its 15 min reminder
22:05:59Z and `marathon.run_live because=schedule` + highlight + shout 22:20:59-22:21:00Z, exactly the PLANNED 22:20:00Z.
The owner's on-screen timer put the real start at about 21:40Z. One GET of `.../api/public/schedules/event/21` at
**2026-10-09T22:45:17Z** (PowerShell `Invoke-WebRequest`, User-Agent `BlackBloc-dev/0.1 (+https://blackbloc.heygabi.ai)`,
200, 73,554 B): 66 items, 56 runs, **22 items carry `actualDuration` (seconds)**: every item before 23 except item 16, the
482-minute *End of Day 1* break, which has none. Item 22 (*Yakuza Kiwami 2*): planned 108 + 25 min = 7,980 s,
`actualDuration` 7,003, `updatedAt` 21:29:56Z (about when it ended).

| Walk | Item 23 starts |
|---|---|
| planned `duration + setupTime` only (the bot before this fix) | **22:20:00Z**, reproduces the bot |
| `actualDuration` where present, as the WHOLE slot (setup included) | **21:27:42Z**, within the transition of the ~21:40Z on-screen start |
| `actualDuration` + the planned `setupTime` after it | drifts later with every finished item; the conductor's run of this variant gave an impossible next-day time |

**Reader.** `parse_fastestfurs(payload, *, actual_includes_setup=True, use_actuals=True)`: a finished item
(`actualDuration` an int >= 0, not a bool) holds the clock for `actualDuration` seconds, plus its planned `setupTime` only
when `marathon_fastestfurs_actual_includes_setup` is OFF; an unfinished item holds it for `duration + setupTime` as before.
`Run` gains `actual_seconds` (a finished run's real length) and `timed_by_actuals` (the item before it finished AND every
earlier RUN finished; an unfinished BREAK such as *End of Day 1* does not break the chain for later items, but the item
right after it is planned-timed). `run_seconds` stays the planned `duration`. A planned-only payload walks exactly as
before (pinned). `actualDuration` 0 is finished and takes no time; a string or a negative number reads as not finished.

**The flag.** `marathon_fastestfurs_actual_includes_setup` (bool, default **on**): the measurement above says the real
length already covers the setup that follows; staff flip it if a future event proves otherwise. It reaches the reader
through `cogs/content/marathon_signals.py` `reader_for` (Fastest Furs only; `setup_for` is unchanged for `resolve`).

**Cadence.** `marathon_sources.PUBLISHES_ACTUALS = {fastestfurs}` / `publishes_actuals`. `marathon.live_minutes` gives
`marathon_live_poll_minutes` (int, default **1**, range 1-60) while the marathon is ON (`phase == ON`: between its
`starts_at` and `ends_at`) and its source publishes actuals; every other marathon (GDQ, RPGLB, horaro, Oengus, Hotfix, Lady
Arcaders, or a Fastest Furs event before it starts) keeps `marathon_poll_minutes` (30) or the far cadence. All four
next-read sites (the loop's `read_due`, the card's reading line, `/api/marathons`, the schedule page) pass it, so the page
shows the same next read the loop uses. Politeness: the loop ticks once a minute (`TICK_MINUTES`), each read is ONE GET with
no retry inside it, and the cadence is keyed per MARATHON (its own `last_fetched_at`); the feed's `/api/events` check keeps
its own 6 h cadence. **Back-off:** after `LIVE_READ_FAILURES` (3) failed reads in a row (`fetch_failures`, which an
unpublished answer does not raise) the marathon falls back to `marathon_poll_minutes`; a success resets it. The existing
`marathon.schedule_stale` row fires once at the third failure; each `marathon.fetch_failed` on such a marathon carries
`live_reads_paused`.

**Re-timing (confirmed, no new code).** A source that re-times itself has `holds() == False`, so a read rewrites
`scheduled_at` of every row incl. live ones; a shift of at least `marathon_move_minutes` logs `marathon.member_run_moved`
and re-arms the reminders (`mrem.run_fields`). A run moved to BEFORE now: the same tick's `follow` -> `advance` (the
schedule decides; with a watched stream it waits `marathon_late_grace_minutes` as for any run) makes it live, and `remind`
runs AFTER `advance`, so `due_marks` sees a live run and **the 15-min reminder is never posted after the live post**
(pinned: `test_a_run_moved_to_before_now_goes_live_at_once_and_never_posts_its_reminder`). A reminder copy ALREADY posted
is left as posted: `sync_reminders` follows upcoming and dropped runs only (`FOLLOWED`), and the run is live before it runs
(pinned: `test_a_reminded_run_moved_to_before_now_goes_live_and_posts_nothing_new`). An edit-at-read pass was tried and
reverted: it doubled the per-tick edit budget and broke `test_the_edit_limit_is_the_keys` and the mode-off test.

**Early-start guard: FINDING, the brief's premise did not hold.** `cogs/content/marathon_signals.py` `guarded` and
`undo_early` return at once for every source where `retimes_itself` is True, Fastest Furs included, so the v202 guard
**never** held a Fastest Furs stream match; it only guards GDQ Hotfix, whose `sheet_at` is rewritten on every read (it is
already the schedule's current best start). What kept Mathcat at 22:20 was the schedule walk alone plus no stream
confirmation (title/category confirms need an open session on the marathon's spotlight channel; that was not checked).
Nothing in the guard was changed; pinned: `test_a_stream_match_on_a_schedule_that_times_itself_is_never_held_as_early`
(a Fastest Furs row 39 min before its OLD sheet time passes) beside the Hotfix pin
`test_a_days_first_run_shown_80_minutes_early_is_held_and_logged_once` (the typo protection).

**Fixture.** `tests/fixtures/marathon/fastestfurs_schedule_actuals.json` (7,738 B): items **0-24** of the 22:45:17Z
payload, each trimmed to `id, runId, itemType, duration, setupTime, actualDuration, orderIndex, label, runs{id, name,
category}`; items 21-24 also keep `updatedAt`, `runs.runners` and host names. Deviation from the brief's "a handful around
21-24": the walk needs every earlier item to reproduce the measured 22:20:00Z -> 21:27:42Z, so the leading items are kept,
stripped.

### What was NOT verified

1. ⚠️ **Nothing met Discord, Fly or a live Fastest Furs read through the bot.** The parser, the cadence and the
   moved-earlier path ran only against the suite's fakes and the saved fixture. **The next live Fastest Furs run after a
   deploy is the proof.**
2. The ~21:40Z real start is the owner's on-screen timer, not a measured stream event; 21:27:42Z vs ~21:40Z is ~12 min,
   read as transition time, not checked against the VOD.
3. Whether `actualDuration` truly includes the following setup is inferred from ONE event's timeline (hence the flag).
4. How the organiser fills `actualDuration` mid-run (only at the end? corrected later?) and the overnight break's missing
   value were seen once, at 22:45Z.
5. A 1-minute read's cost on `cheetah.fastestfurs.com` (73 KB per GET, about 60 GETs an hour per live marathon); no rate
   limit was measured.
6. Whether the marathon had an open stream session (title/category confirms) on 2026-10-09 was not read from the live DB.
