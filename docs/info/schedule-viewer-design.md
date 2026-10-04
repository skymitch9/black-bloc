# Schedule viewer — a run sheet per marathon, with live staff re-timing

> **Audience:** the owner (to agree the design), then the build agent. **Status:** TRACKED.
> 🏷️ **2026-10-03 (owner): the page is named *Marathon tracker* and lives at `/schedule.html#marathon-<id>`;
> its read is `GET /api/marathons/{id}/schedule`.** Verbatim: *"i dont want it to be called a runsheet, call it a
> marathon tracker and make the url schedule"*. Older sections below keep the words they were written with
> ("run sheet", `/runsheet`); read them as the same page.
> 🔨 **READ-ONLY VERSION BUILT on branch `runsheet-live` (2026-10-03), NOT merged, NOT deployed** — the page on the
> real bot, updating itself: see *Live, read-only 2026-10-03* at the end. 📐 **The staff re-timing moves are still
> DESIGN — NOT AGREED**; every item under *Open decisions* is the owner's, and they exist only on the mock
> (*Prototype 2026-10-03*).
> Last verified: **2026-10-03 20:4x Phoenix** — the facts under *What exists today* were read off
> `main` at `455cce06` (the run table in `storage/db.py`, the routes in `api/tools/marathons.py`,
> `marathon_sources.RETIMES_ITSELF`) and the live action log for GDQueer day 1. ⚠️ **NOT checked:**
> the site's marathon drawer was not opened in a browser for this doc; the Discord thread controls
> were read as code, not seen; nothing here has met a real marathon.
> Mock to react to: the *Run Sheet Mock* artifact linked from [`../TODO.md`](../TODO.md) ▸ chunk 5.

## The ask (owner, 2026-10-03, verbatim)

*"for the gdqhotfix that doesnt have a live tracker I want to build one. This will give our staff
the ability to dynamically update run times for our events. I pretty much want a schedule viewer
for each event. if it has an api then just consume that and show me, if it doesnt like hotfix lets
build one. see what we can scrub from that github link and check the repo too. … the goal is we
might be ahead or behind on schedule and having a way to update times live so the bot can consume
it would help have more accurate times for posting."*

## The problem, measured

GDQueer day 1 (2026-10-03). The bot's first prediction for JR's run was 12:50; it went live at
13:22. Stream re-timing caught each run as it started, but between confirmations the bot's times
were early by a median of 7 minutes, and nobody on staff could tell it "we are running ten
behind". The only staff moves on a run today are *live*, *done*, *upcoming* and *back to the
sheet's times* — none of them sets a time.

## What exists today (so the build adds a surface, not a second engine)

| Piece | Where | What it already does |
|---|---|---|
| Three times per run | `marathon_runs`: `sheet_at`, `scheduled_at`, `actual_started_at` / `actual_ended_at` | the source's time, the bot's current prediction, and what really happened |
| Run state | `state`: upcoming / live / done / dropped; `live_because` | set by the stream (title, category) or by staff |
| Staff moves | `POST /api/marathons/{id}/runs/{run}/live` · `/done` · `/upcoming`, `POST …/sheet-times` | mark a run, or throw away re-times |
| Re-timing | `marathon_signals.retimed` | a confirmed start anchors the run; later runs that day follow it (estimate + `marathon_setup_minutes`) |
| Who re-times | `marathon_sources.RETIMES_ITSELF` | trackers (GDQ, RPG Limit Break, horaro, Oengus, Fastest Furs, Lady Arcaders) publish their own moving times; Hotfix does not |
| What follows a time | reminders (24 h / 2 h / 15 min), highlights, runner posts, events, ping windows | all read `scheduled_at` — move it and they move |
| The schedule on the site | Events ▸ a marathon's drawer ▸ *The schedule* | a list by day and slot, for linking people — no times can be changed |

So the viewer needs **one new thing in the data** (a time a person set, and who set it) and
**one new surface** (a page built for running a show, not for linking people).

## The design

### 1. One run sheet per marathon

Every marathon gets a run sheet: the day's runs in order, each with its start, estimate, game,
category, runners, host, and state. BaF people are marked. The top of the sheet says in one line
where the show stands: **Running 6 min ahead** / **12 min behind** / **On time**, measured from the
last confirmed start against the source's time for that run, and when the bot last read the source.

### 2. Two kinds of sheet, decided by the source

- **The source moves its own times** (any tracker): the sheet is **read-only for times**. It shows
  what the tracker says, re-read on the existing poll. Staff can still mark a run live or done.
  Reason: a time typed here would be overwritten at the next read, and two clocks is the bug.
- **The source never moves** (Hotfix; a schedule staff typed in — see decision 2): the sheet is
  **editable**. Staff are the tracker.

### 3. The staff moves on an editable sheet

| Move | What it does | Later runs that day |
|---|---|---|
| **Started now** | the run is live from this minute (today's *live* move) | follow from here |
| **Finished now** | the run is done from this minute (today's *done* move) | next = now + setup |
| **Set start…** | this run starts at the time typed | keep their gaps |
| **We're behind / ahead** | every run not yet started moves by ±5, ±10 or a typed number | all move together |
| **Change estimate…** | the run's length changes | follow |
| **Skip this run** / **Bring it back** | the run is dropped / restored | close the gap / reopen it |
| **Back to the source's times** | forget every staff time for the day (today's *sheet-times* move) | reset |

Every move: one press, takes effect at once, writes an action row naming who and the before/after,
and can be undone (staff final say — no move is terminal). A run that is live or done is never
moved by a move on another run.

### 4. Whose time wins

Highest first: **what really happened** (stream confirmation, or staff *Started now*) → **a time
staff set** → **the organisers' own sheet** (when the event has one) → **the source sheet +
`marathon_setup_minutes`**. A later stream confirmation beats an earlier staff time; a later staff
move beats an earlier stream guess (staff final say). The sheet shows which of the four each
run's time came from.

### 5. How the bot consumes it

No new path. A staff move writes `scheduled_at` through the same re-time function the stream
uses, so reminders, highlights, runner posts, events and ping windows follow as they do today.
New column(s) on the run: the staff-set start and estimate, who, when. A moved run whose reminder
already went out is handled by decision 7.

### 6. Two doors (house rule: a panel, and both ways)

- **The site:** the run sheet page, opened from the marathon's drawer and from the Events list.
- **Discord:** the marathon's staff thread gets the same moves on its pinned controls —
  *Started now*, *Finished*, *Behind 5*, *Ahead 5*, *Set time…* — for whoever is watching the show
  on their phone. Buttons show only when valid.

### 7. What is taken from the ScheduleViewer repo

Its layout ideas — a day strip, shows grouped under a header, columns Game / Start / Estimate /
Runner, a timezone picker — and its host → Twitch table (through the `hotfix-viewer-source`
build). **No code or logo files are copied:** the repo has no licence.

### Not in the first build

Reordering runs by drag; editing a tracker marathon's times; a member-facing public page (decision
6); anything that posts a new kind of message.

## Open decisions — the owner's, asked one at a time

1. **Where it lives.** A full page per marathon (recommended: a show needs room, and a link staff
   can keep open), or a bigger *schedule* section inside the existing marathon drawer.
2. **Schedules typed by staff.** *"for our events"* — should staff be able to build a schedule
   from nothing (paste rows or type them) for a BaF-run event with no source at all, in the first
   build, or only re-time schedules the bot already reads?
3. **Which moves are in the first build.** All seven above, or the short list: Started now,
   Finished now, Behind / Ahead, Set start.
4. **Who may move times.** Staff only (recommended), or also the BaF runner / host of that run for
   their own slot.
5. **The Discord door.** In the first build, or the site first and Discord after.
6. **A member-facing view.** Staff only (recommended to start), or also a read-only schedule
   members can see.
7. **A post that already went out.** When a run moves after its heads-up was posted: edit the post
   in place with the new time (recommended), or post again.
8. **Trackers.** Strictly read-only for times (recommended), or let staff override a tracker time
   until the tracker's next change.

## Deviations

None from a bot build — nothing on the bot side is built. The local prototype's are listed under
*Deviations — prototype 2026-10-03* below.

## Prototype 2026-10-03 — a real local page on the mock (branch `runsheet-proto`, NOT merged)

> **What this is:** the site half of this design, built against the mock so the owner can press
> the buttons. **Nothing in `black_bloc/` exists for it** — no routes, no columns, no Discord door.
> Measured 2026-10-03 ~21:00 Phoenix on the branch: the page rendered in headless Chrome at
> 1280 px and 390 px (blackbloc dark, apple light, classic light, cyberpunk dark) with no horizontal page scroll
> and no console error; every move pressed in the browser or walked through the API
> (`MOCK_PORT=8798 node site/mock/runsheet.test.mjs`). ⚠️ **NOT checked:** the other three themes,
> a real phone, a keyboard-only pass, a screen reader, a marathon of 150 runs, and anything on the
> bot side.

### How to open it

```
MOCK_PORT=8798 MOCK_TEST_MODE=0 node site/mock/server.mjs
```

| Sheet | Address | What it is |
|---|---|---|
| Editable | `http://localhost:8798/runsheet.html#marathon-60` | **GDQueer (run sheet)** — a Hotfix marathon seeded for this page (below) |
| Read-only | `http://localhost:8798/runsheet.html#marathon-1` | **AGDQ 2027** — a GDQ tracker marathon, three days |
| From Events | `http://localhost:8798/events.html` ▸ Marathons | a **Run sheet** button on every row and at the top of every marathon's drawer |

`POST /api/mock/reset` (or restarting the mock) puts the seed back; the seed is rebuilt around the
moment it is made, so the third run of the day is always live.

### What the page does

- **Top:** *← Events* (opens that marathon's drawer) and a marathon picker. The address is
  `runsheet.html#marathon-{id}`, the same hash the Events drawer uses.
- **Header card:** the marathon and the day, one status pill (*Running N min ahead* / *behind* /
  *On time* / *Every run has started*), the source link, where the times come from, when the
  source was last read, the zone times are shown in, and one sentence saying which kind of sheet
  this is.
- **Day strip** when the marathon has more than one day.
- **Day bar (editable sheets):** *Behind 5 · Behind 10 · Ahead 5 · Ahead 10*, a typed number with
  *Behind* / *Ahead*, and *Back to the source's times* (drawn only while the day carries a staff
  time or estimate).
- **Notice + Undo last move:** every move answers with one sentence of what changed; the Undo
  button is drawn while there is a move to take back and its tooltip names it.
- **The sheet:** one row per run — start (large, tabular), a tag for where that time came from,
  *sheet said HH:MM* when it differs, game, category, estimate (tagged when staff set it),
  runners and host as the drawer's chips with `✦BaF`, state, and the moves. The live row is
  tinted. The next run not yet started carries **Started now**; the live run **Finished now**;
  every other move for a row is behind its **Edit…** (new start, estimate, *Started now* for a
  run that is not next, *Skip this run*). A skipped run shows **Bring it back**. A search box
  (the shared `listFilter`) appears from 12 rows.
- **What the bot posts next:** for the day shown — a live BaF run's highlight, the heads-up for
  each upcoming BaF run, and one heads-up per BaF host block (consecutive runs with the same BaF
  host, announced at the block's first run). Each time is the run's current start minus the
  smallest number in `marathon_reminder_minutes`.
- **Moves today:** who, when, what — newest first; a move that was undone is marked.
- The page asks again every 60 s while no row is being edited.

### The mock routes — the contract the bot's routes will be built to

All under `/api/marathons/{marathon_id}/runsheet`, staff only, refusals in the usual
`{error, message}` shape. Every POST answers the same body as the GET plus `message`.

| Method + path | Body | Refuses (error) |
|---|---|---|
| `GET` | — | `not_found` |
| `POST …/runs/{run_id}/start` | — | `not_startable` (not upcoming), `no_such_run` |
| `POST …/runs/{run_id}/finish` | — | `not_live` |
| `POST …/runs/{run_id}/set-start` | `{time: "2:30 PM", zone: "America/Denver"}` — a clock read in `zone` (the zone the page is showing; a missing or unknown zone falls back to `default_timezone`); the nearest such moment to the run's current start. See *Times, zones and the 12-hour clock* | `tracker_times`, `not_movable`, `bad_time`, `same_time`, `before_the_run_ahead` |
| `POST …/shift` | `{day: "<key>" \| "today", minutes: ±1…240}` | `tracker_times`, `bad_minutes`, `no_such_day`, `nothing_to_move`, `before_the_run_ahead` |
| `POST …/runs/{run_id}/estimate` | `{estimate: "1:20" \| "45"}` (1 min – 12 h) | `tracker_times`, `not_movable`, `bad_estimate`, `same_estimate` |
| `POST …/runs/{run_id}/skip` · `…/restore` | — | `tracker_times`, `not_skippable` · `not_skipped` |
| `POST …/reset` | `{day}` | `tracker_times`, `no_such_day`, `not_retimed` |
| `POST …/undo` | — | `nothing_to_undo` |

The GET's body:

```
marathon        {id, name, source, source_word, schedule_page, phase, phase_word, last_fetched_at,
                 channel_login, watch_url (https://www.twitch.tv/<channel_login>, or null)}
editable        true for a source that never moves its own times (the mock's MARATHON_KEEPS_CLOCK)
kind            "editable" | "read_only"
times_from      "organisers" | "source" | "tracker"      times_from_word   the same in words
timezone        default_timezone — the page's FALLBACK zone only; every time in this body is an ISO moment
now             the server's clock
setup_minutes   marathon_setup_minutes                    heads_up_minutes  min(marathon_reminder_minutes)
today           the key of the day with the live run, else the first with a run still to start
days[]          {key (opaque), label (in the server zone — the page labels the day from starts_at), starts_at, runs, baf, drift_minutes, drift_run_id,
                 staff_times, staff_estimates, can_shift, can_reset}
rows[]          {id, day, order_no, game, category, people[{name, login, part, user_id, member_name, baf,
                 twitch_url, twitch_from, youtube_url, youtube_from, link_from}],
                 ours, state, state_word, start_at, ends_at,
                 from: stream | started | staff | organisers | source | follows | tracker,
                 plan_at, plan_from, off_plan_minutes, estimate_seconds, estimate_from, source_estimate_seconds,
                 actual_started_at, actual_ended_at, staff_at, next_up,
                 can{start, finish, set_start, estimate, skip, restore}}
next_posts[]    {at (null = up now), kind: live | run | host, run_id, day, passed, text}
moves[]         {id, at, by_id, by_name, kind, text, undone}          newest first
undo            {available, text}
```

Action kinds written: `web.marathon.runsheet_started` · `_finished` · `_start_set` · `_shifted` ·
`_estimate_set` · `_skipped` · `_restored` · `_reset` · `_undone`, each with `marathon_id`, the
run or day, and `before` / `after`.

### Times, zones and the 12-hour clock (added 2026-10-03, owner: "have the website get timezone from cookies to always show local time for the person. also lets use am pm and not 24 hour time")

**One formatter, in the page.** The API returns moments and never a formatted time. Row times,
`days[].starts_at`, `next_posts[].at` and `moves[].at` were already ISO; the answer sentences
(`message`, `moves[].text`, `undo.text`, and the refusals that name a time) now carry the moment
as a token — `{{at:2026-10-04T19:03:00.000Z}}` for a clock, `{{day:<ISO>}}` for a day — and the
page fills them (`timezone.js` `fillMoments`). So a sentence already on the page re-reads in the
new zone the moment the viewer switches, and the mock holds no clock formatter at all. The bot's
routes should do the same: moments out, tokens in sentences.

**The zone in use**, first hit: a zone the viewer PICKED on the page → the browser's own
(`Intl.DateTimeFormat().resolvedOptions().timeZone`) → the one remembered in the cookie (when
the browser gives none) → the payload's `timezone` (the server's). An unknown zone anywhere is
skipped, never an error. One small line in the header card says which: *Times shown in your time
— America/Denver* (or *Times shown in Asia/Tokyo time* when picked, *…the server's time…* on the
fallback), beside a picker: *My device's time (…)* plus the zones in the `timezone_choices`
setting (the shared `ui.js` `zoneSelect`).

**The cookie:** `bb_tz`, `Path=/`, `Max-Age=34560000` (400 days), `SameSite=Lax`, not HttpOnly
(the page writes it). Value: the URL-encoded zone, e.g. `America%2FDenver`; a picked zone is
`pick%3AAsia%2FTokyo`. Rewritten on every load; *My device's time* deletes it and the next paint
writes the device zone again. Nothing server-side reads it in the prototype.

**The format:** `12:03 PM` — hour with no leading zero, two-digit minute, one ordinary space,
upper-case AM / PM. Everywhere: rows, *sheet said*, posts, moves, tooltips, sentences. Days read
`Sun 4 Oct`. Estimates stay durations (`1:50`). On the sheet the AM / PM is set smaller than the
digits so the clock column still fits a phone.

**Set start… accepts** `12:40 pm`, `12:40pm`, `1240pm`, `12:40 PM`, `12.40 p.m.`, `7pm`, and
24-hour `13:40` / `1340`. A clock with no am/pm and an hour from 1 to 12 (`1:40`) is taken as
whichever of AM and PM is nearer the run's current start. It is read in the zone the page is
showing (the form says so, and sends it as `zone`), and the answer echoes the time it understood.
Refused: `25:99`, `13pm`, `0:30 am`, `12:60pm`, a bare `7`, words — with *Type it like
**2:30 PM** (or 14:30) — it is read in <zone> time.*

**A day** is still a block of runs; its label is the date its first run falls on in the viewer's
zone, so the same block reads *Sat 3 Oct* in Phoenix and *Sun 4 Oct* in London.

### Channel links on names (added 2026-10-03, owner: "lets make clicking a host or the runner link to a twitch and or youtube channel if we know it")

Every runner and host name on the sheet is a link when a channel is known, plain text when not.
The lookup is the mock's (`site/mock/runsheet.mjs` `channelsOf`), never the page's.

| Case | What the name looks like |
|---|---|
| Twitch only | the name chip is a link to Twitch (a small ↗ on the chip), new tab |
| Twitch and YouTube | the name chip links to Twitch; a second small chip reading **YouTube** sits right beside it and links to YouTube. The pair wraps together, so at phone width the YouTube chip drops under the name rather than splitting |
| YouTube only | the name chip links to YouTube |
| Nothing known, or a link that is not Twitch / YouTube | the same chip as before, plain text, no ↗ |

A race links each person on their own chip. `✦BaF` and the `host` word stay inside the chip. The
tooltip says the part, the site and where the link came from. The header card carries **Watch on
Twitch ↗** when the marathon has a channel.

**Precedence, per site (Twitch and YouTube are settled separately), first hit wins:**

1. `member` — the person is matched to a server member: that member's go-live Twitch link
   (`/api/golive/links`) and their YouTube link (`/api/youtube/links`);
2. `schedule` — the link the schedule gives for that person (`person.url`), or, where a schedule
   gives only a Twitch login (the trackers), `https://www.twitch.tv/<login>`;
3. `hosts` — hosts only: a host-name → Twitch table (`HOST_CHANNELS`, the ScheduleViewer page's
   idea; names matched case-insensitively).

`twitch_from` / `youtube_from` name the source of each (`member` | `schedule` | `hosts`), and
`link_from` is the source of the link the NAME carries (Twitch's when there is one, else
YouTube's). All five are `null` when nothing is known.

**What may be emitted.** Only `https://twitch.tv/<login>` / `https://www.twitch.tv/<login>`
(login = 2–25 letters, digits, underscores) and `https://youtube.com/…` /
`https://www.youtube.com/…` as `@handle` or `channel/UC…`. Anything else from the schedule —
another host, `http:`, a path, a query string — is dropped and the name is plain text; a dropped
link does NOT fall back to a login guessed from the name. The page checks the address again before
it makes an anchor. Links open with `target="_blank" rel="noopener"`.

**Fake in the seed:** every day-2 runner has a `twitch.tv/<their sheet name>` link except
Lunch_the_great (none) and Ramseyfox (a `http://…example` link, there to show the drop);
champrul is tied to the mock member Casey, so the name links to `twitch.tv/caseyfast` with a
YouTube chip — the mock's link rows, not champrul's real channels (the both-links case; it was
JRisJunior until the owner said, 2026-10-03, "jrisjunior isnt our guy"); JRisJunior is an ordinary
host with no link and is in no table; the host table holds Quacksilver → QuacksilverPlays,
anarchy → anarchyasf, sweetpeebs and chibicarrera. SYDNEY J is in no table and stays plain text.
Marathon 60 now sits on the mock's `gdqhotfix` channel row.

⚠️ **Not decided, the owner's:** whether a staff-set pairing Twitch name (the drawer's *Twitch
name…* fix) should sit above the member's go-live link. The prototype does not read it.

### The recompute (one place: `site/mock/runsheet.mjs` `sheetOf`)

Runs are taken in sheet order. A gap of more than four hours between one run's sheet end and the
next run's sheet start begins a new **day**; nothing ever carries across days. Within a day, per run:

1. it really started (`actual_started_at`) → that time (*seen on stream*, or *started by staff*);
2. it is live or done with no recorded start → its stored time, untouched;
3. staff set a time (`staff_at`) → that time (*set by staff*);
4. otherwise the first run of the day takes its sheet time, and every later one starts where the
   run before it ends plus **its own setup gap** — the gap the sheet left before it. When that
   lands on its sheet time the tag is *organisers' sheet* (or *source sheet + setup* when the event
   has no organisers' sheet); when it does not, *follows the run before*.

A run ends at its recorded finish, else start + estimate (staff's estimate when there is one); a
live run that has outrun its estimate ends *now*, so the next run waits for it. A skipped run has
no time and the next run takes only its own gap, which closes the hole. After every move the mock
writes each run's `scheduled_at` / `ends_at` from this, which is how the Events drawer and the
*next posts* panel follow.

What each move changes: **Started now** — the run is live from this minute, any other live run
is finished at the same minute, and staff times on later runs of that day are dropped (they
follow reality). **Finished now** — the same drop. **Set start** — `staff_at` on that run; later
staff times move by the same amount. **Behind / Ahead** — `staff_at` on the first run not yet
started (its current start ± N); later staff times move with it. **Estimate** — a staff estimate
on that run. **Skip / Bring it back** — the run's state. **Back to the source's times** — drops
the day's staff times and staff estimates; real starts and finishes stay, and so do skips.
**Undo** — puts every run of the marathon back as it was before the last move (50 deep).

### What is fake

- **The whole bot side.** The mock is the only thing that answers these routes; the moves log and
  the undo stack live in the mock's memory and go at a restart or `POST /api/mock/reset`.
- **Marathon 60, *GDQueer (run sheet)*.** A new seed marathon rather than a change to GDQueer
  (50): `check.mjs` pins 50 as the re-timed marathon for *Back to the sheet's times*, and two
  other branches were editing its seed. Its day 2 is the real organisers' sheet for Sun 4 Oct —
  eleven runs, their estimates, runners, hosts and 10-minute setups — but **moved to the present**:
  the third run's sheet time is two minutes from the moment the seed is made, so the clock on the
  page is whatever the wall clock is, not 10:00–21:49 Phoenix. The first two runs are done, the
  third went live five minutes ahead of its sheet time. Its "source sheet" times are invented
  (the same runs chained with a 7-minute setup). Day 1 is three finished runs a day earlier, there
  only so the day strip shows on an editable sheet.
- **BaF people.** The_Mathcat and champrul are tied to two mock members (Dax, Casey) so the `✦BaF` mark and the posts panel have something to show.
- **The posts panel** is worked out from the sheet; nothing is posted, and "its time has passed"
  is only the clock, not a record of a post having gone.

### What is red on the branch, and why

`site/mock/contract.json` carries `/runsheet.html`, six run-sheet routes and nine
`web.marathon.runsheet_*` kinds so `check.mjs` walks them. The Python half reads the same file,
so on this branch `tests/api/test_contract.py` is red for exactly those six routes
(`test_every_route_answers_with_the_keys_the_pages_read[…/runsheet…]`: the bot answers 404 / 405
`unknown_route`). Measured 2026-10-03 21:1x from the worktree: **6 failed, 9,863 passed, 3 skipped**
over the whole suite; `check.mjs` against this branch's mock: **ok — 23 pages, 294 routes**; the
eleven node fixtures green. The page and the nine kinds fail nothing on the Python side today.
That is the reason the branch stays unmerged until the bot side is built.
Set-start, restore, reset and undo are **not** in `contract.json` (they need a moment or an
earlier move a fixed body cannot give); `runsheet.test.mjs` walks them instead. That fixture is
not wired into `scripts/deploy.ps1` or CI.

## Deviations — prototype 2026-10-03

1. **The status line measures the next run NOT YET STARTED**, falling back to the live run when
   nothing is left to start. §1 says "from the last confirmed start". Measured on the live run,
   *Behind 10* left the line reading "5 min ahead" — the move showed nowhere at the top.
2. **A sixth tag, *started by staff*.** §4 folds staff's *Started now* into "what really
   happened"; on the sheet it reads differently from *seen on stream*, so staff can tell which
   starts a person vouched for. Trackers get a seventh, *from the tracker*.
3. **Started now / Finished now drop the staff times on later runs of that day.** §4 says a later
   confirmation beats an earlier staff time; the prototype applies that to every later run, not
   only the one confirmed, so "next = now + setup" holds. ⚠️ It also drops a time staff typed for
   a far later run (say, after a break). The owner should say whether such a time must survive.
4. **Started now also finishes whichever run was live**, at the same minute. Not in §3; it is what
   pressing it during a show means, and Undo takes both back.
5. **A day is a block of runs, not a calendar date**: a sheet gap over four hours starts a new one.
   The bot's `marathon_signals.chains` uses the setup-key reach; the two should be made one rule
   when the bot side is built.
6. **Set start and Behind / Ahead refuse a time before the start of the live or done run ahead**
   (`before_the_run_ahead`). Not in the design.
7. **The rows show the schedule's own name with `✦BaF`** (the member's name is the tooltip), where
   the drawer shows the member's name. On a run sheet the name on the layout is the one staff are
   looking for.
8. **Only the next run shows *Started now* on its row** on an editable sheet; the rest keep it
   behind **Edit…**. On a read-only sheet every upcoming run shows it, since nothing else is there.
9. ~~No timezone picker~~ — SUPERSEDED the same day: times are in the viewer's own zone with a
   picker (*Times, zones and the 12-hour clock*). ⚠️ The run sheet is now the ONLY page that does
   this; the Events drawer still shows `default_timezone` in 24-hour, so the two disagree until
   the rest of the site follows.
10. **The Discord door (§6) is not built**, and decision 7 (a post that already went out) is not
    modelled — the posts panel only shows where the times would land.
11. **The run sheet uses its own start / finish routes**, not `…/runs/{id}/live` and `/done`:
    those carry no undo and re-time with the older rule. The drawer's buttons still work on these
    marathons, but a press there is not in *Moves today* and cannot be undone from the sheet.
12. **Starting a run out of order is not handled.** *Started now* on a run that is not next
    leaves the runs skipped over as upcoming, at times after it. Staff would skip them by hand.

## Live, read-only 2026-10-03 — the Marathon tracker on the real bot (branch `runsheet-live`, NOT merged)

> **Owner, verbatim:** *"we need to have the schedule run sheet that auto updates to live tracking times link to
> each marathon ... for now lets send the schedule pages live with auto updates"*, then *"i dont want it to be
> called a runsheet, call it a marathon tracker and make the url schedule"*.
> **Measured 2026-10-03 ~22:30 Phoenix on the branch:** `ruff check black_bloc tests site` clean; the whole suite
> **10,149 passed, 3 skipped**; `check.mjs` against this branch's mock **ok — 23 pages, 291 routes**; all eleven
> node fixtures green; 52 of 52 `site/public/assets/*.js` parse as modules. The real route's payload was built
> from a database seeded through the real cog with the GDQueer Hotfix sheet and the organisers' sheet laid over
> it (`tests/fixtures/marathon/`), three runs seen on stream, one dropped, a BaF runner and a BaF host — and
> printed. The page was driven in headless Chrome against the mock at 1280 px and 390 px: one auto-update was
> watched (below). ⚠️ **NOT checked:** the page against the real bot in a browser (the real payload was read as
> JSON, the page was read against the mock's copy of the same shape); a real phone; a keyboard-only pass; a
> screen reader; the themes other than blackbloc dark; a marathon of 150 runs; the Discord link button in a real
> client; anything on production.

### What is live in this version

| Piece | State |
|---|---|
| The page `schedule.html#marathon-<id>` reading the real bot | built |
| It re-reads itself | built |
| **Started now** / **Finished now** | built — they call the EXISTING `POST /api/marathons/{id}/runs/{run}/live` and `/done`, then re-read |
| A **Marathon tracker** button on every marathon row and drawer on Events | built (the prototype's, renamed) |
| A **Marathon tracker ↗** link button on each tracked marathon's pinned thread controls | built |
| Set start, Behind / Ahead, estimate, skip, bring back, back to the source's times, undo | **mock only** — `can` is `false` for all of them on the bot and the page draws none of them |
| A member-facing view | not built — the route is behind the same staff sign-in as every other marathon GET |

No schema change (86), no new write route, no new action kind.

### The route

`GET /api/marathons/{marathon_id}/schedule` — `black_bloc/api/tools/marathon_schedule_page.py` (reads the rows
and asks the tick's own functions what it would post) over `black_bloc/marathon_schedule_page.py` (pure: rows in,
payload out). Staff only, as `GET /api/marathons/{id}` is. An archived marathon answers too, as the detail route
does, with `marathon.archived: true`, phase `archived`, every `can` false and no `next_posts`. An unknown id is
`404 not_found` in the detail route's words.

The body is the prototype's (*The GET's body* above) with these differences:

| Key | On the bot |
|---|---|
| `editable` | `false` for every marathon |
| `kind` | `tracker` (the source moves its own times) or `clock_kept` (Black Bloc keeps the clock: Hotfix). The mock now says the same two words |
| `moves_by` | `marks` — Started / Finished now go to the existing `…/runs/{run}/live` and `/done`. The mock says `tracker` on its editable sheets (its own move routes) and `marks` on its tracker sheets |
| `refresh_seconds` | the `marathon_tracker_refresh_seconds` key |
| `marathon.next_read_at`, `marathon.archived` | added |
| `days[].upcoming` | added — runs not yet started that day |
| `days[].drift_minutes` | `null` on a tracker until a run has really started (below) |
| `rows[].from` | one more word, `held` (below); never `staff` |
| `rows[].start_at` | what really happened when known (`actual_started_at`), else `scheduled_at` |
| `rows[].ends_at` | the stored end — a live run past its estimate is NOT stretched to now, as the mock does |
| `rows[].estimate_from` | always `source`; `staff_at` always `null` |
| `rows[].can` | `start` where `marathon.can_mark_live` allows (upcoming or done), `finish` where the *Mark done* rule allows (upcoming or live); the other four `false` |
| `next_posts[]` | each mark still to fire, with `minutes` and `role` (below); `kind: live` only when the run's shoutout is up |
| `moves[]` | the marathon's action rows, not a staff-move book (below); `undone` always `false` |
| `undo` | `{available: false, text: null}` |

### Where a time came from — how each tag is derived

Only stored facts. `plan` is the run's `sheet_at` (else `scheduled_at`).

| Tag | Rule | Words on the page |
|---|---|---|
| `stream` | `actual_started_at` is set and `live_because` is not `staff` | seen on stream |
| `started` | `actual_started_at` is set and `live_because` is `staff` | started by staff |
| `tracker` | no real start, and the source moves its own times | from the tracker |
| `organisers` | clock-kept, no real start, the start equals the plan, and the marathon's organisers' sheet is applied (`overlay_sheet.applied`) | organisers' sheet |
| `source` | the same with no sheet applied — the plan is the Hotfix sheet plus `marathon_setup_minutes` | source sheet + setup |
| `follows` | clock-kept, no real start, the start differs from the plan, and an EARLIER run of the same day has a real start or a real end | follows the run before |
| `held` | clock-kept, no real start, the start differs from the plan, and nothing earlier that day really started or ended | kept from an earlier read |
| *(none)* | a dropped run: no time, no tag | — |

**What cannot be told apart from stored data, and what the page says instead:**

1. **A real start seen on stream vs marked by the schedule's clock.** A run the clock alone called live has no
   `actual_started_at`, so it is tagged by its stored time (`organisers` / `source` / `follows` / `held`), never
   `stream`. That is honest: nobody saw it start.
2. **Staff pressing *Mark live* on a run the stream then confirms.** `live_because` moves to the stream's word,
   so the tag reads `stream` although the moment is the staff press.
3. **`organisers` for a run the sheet did not pair.** With the sheet applied, a run with no slot starts where the
   run before it ends; its `sheet_at` holds that computed time, so it is tagged `organisers`. The marathon's
   `overlay.sheet.matched` / `runs` on the drawer says how many paired.
4. **`held`.** A live or done run of a clock-kept schedule is never moved by a read (`holds`), so after the
   setup key or the organisers' sheet changes its stored time no longer equals the plan and nothing explains
   it. `follows` would be a guess; `held` says only what is known.
5. **A tracker's "plan".** A tracker's `sheet_at` is its current time, so an upcoming run is never off plan. The
   header says **Following the tracker** rather than *On time*, and drift is measured only on a run that really
   started (its real start against the tracker's time for it).

### People, the BaF mark and links

`baf` on a person is the People card's rule: matched to a member (`user_id`), and **a commentator never is**.
A row is `ours` when anyone on it is. ⚠️ This is NOT `marathon.is_ours`: a BaF host does not make a run "ours"
for the tick while `marathon_hosts_count_as_ours` is off, yet the host is marked ✦BaF here, as on the People card.

Links, per site, first hit wins: the member's go-live Twitch (`golive_links`) and YouTube (`youtube_links`) →
the schedule's own Twitch name (`sheet_login` when staff fixed the name, else `login`; never a name the viewer
lent) → for a host, the viewer's host table (`login_from = viewer`). Only `https://www.twitch.tv/<login>`
(2–25 letters, digits, `_`), `https://www.youtube.com/@handle` and `…/channel/UC…` are ever emitted; anything
else is dropped and the name is plain text. ⚠️ A Twitch name **staff fixed on a pairing** is not used as a link
(the open question under *Channel links on names*).

### What the bot posts next

For a marathon the tick reminds (active, `marathon_mode` not off, tracked): each upcoming BaF run's marks from
`marathon.reminder_marks` that are not in `reminders_sent` and that `marathon.due_marks` would not skip as stale.
For host blocks (the host switches, public reminders, announcements and a reminder channel all on):
`marathon_host_highlights.blocks` and each block's own record (`claim`), the same way, for blocks none of whose
runs has started and whose hosts are not all opted out. `role: true` on the ping mark when
`marathon_role_ping.verdict_for` mentions and the run has someone not opted out (runs), or `role_for` mentions
(blocks). `passed: true` means the moment has come and the next tick posts it — the page says *due now*.
⚠️ Not modelled: a public copy skipped because the staff copy already sits in the same channel.

### What changed (`moves[]`)

The marathon's action rows of these kinds, newest first, at most 30: `marathon.retimed`, `run_live`, `run_done`,
`run_reset`, `member_run_moved`, `schedule_changed`, `overlay_applied`, `overlay_dropped`, `sheet_times` (and
their `web.` twins). Each is a sentence with its moments as `{{at:ISO}}` tokens. A row with an actor carries the
staffer's name; a caller who may not see names gets `by_id` and `by_name` `null` (every caller is staff today).

### Auto-update

- The page re-reads the route every `refresh_seconds` (one-second tick; the read is skipped while the tab is
  hidden and made at once when it shows again).
- A read is applied by KEY, not by repainting: each card and each run row keeps its node unless what it shows
  changed, so scroll, focus, the notice and the zone picker stay. A row whose panel holds a typed field is left
  alone until it is closed; a card holding the focused input is left alone until focus leaves.
- A row that went live, went done, moved or is new is outlined for 8 seconds (`data-flash`); with
  `prefers-reduced-motion` it is a still outline.
- One line under the header: *Updated 12 seconds ago · re-reads every 30 seconds while this tab is showing*. A
  failed read: *Could not update just now — <why in words> The times below are as they stood at 10:12 PM. Trying
  again in 7 seconds.* — never a status number; the last good sheet stays up.

**Watched, 2026-10-03 22:23 Phoenix, headless Chrome 1280 px, mock on a spare port, key at 10 s:** AGDQ's sheet
open; *Celeste* marked live through `POST /api/marathons/1/runs/6/live` from outside the page; **8 s later** its
row read *live / started by staff* with the outline, the header went from *Following the tracker* to *Running 20
min ahead*, a marker left on another row's node was still there and the status line was the same node. Then
**Finished now** pressed in the page: the row went *done*, the notice read *Celeste is marked done.*, and
**More…** on it offered *Mark live again*. With the read made to fail, the status line read the sentence above
in the warn tone, the notice stayed, and the next good read cleared it. On the mock's editable sheet a time
typed into **Edit…** was still there, focused, after a read.

### The keys

| Key | Type | Default | Bounds | What |
|---|---|---|---|---|
| `marathon_tracker_refresh_seconds` | int | 30 | 10–300 | seconds between reads on the page; rides the payload as `refresh_seconds` |
| `marathon_controls_tracker` | text | `Marathon tracker ↗` | 80 chars shown | the link button's label on the thread controls |

Both are in the registry, so Settings ▸ Marathons and `/settings set-value` reach them; both have a label in
`labels.js` and a row in the mock.

### The Discord link

`marathon_thread_controls.tracker_url(origin, id)` → `<site_origin>/schedule.html#marathon-<id>`. It is the LAST
item of the pinned controls' view, a link button (no custom id). The switches are six or seven (seven when the
Event schedule button shows), so Discord lays them five on the first row and the rest on the second; the link
sits on that **second row**, after the switches — 7 or 8 of the 25 a message may carry. It is part of what
`refresh_controls` compares, so a posted message gains it at the next tick after a deploy (the cache is empty
at boot) and takes a changed label within a tick.

### Names chosen (the rename)

| Thing | Name | Why |
|---|---|---|
| The page, what people read | **Marathon tracker** | the owner's word |
| The address | `/schedule.html#marathon-<id>` | the owner's word. ⚠️ No clean `/schedule`: the bot serves pages with `StaticFiles(html=True)` and the mock by file path, and neither maps a bare path to its `.html` — adding that would be a new mechanism |
| The API | `GET /api/marathons/{id}/schedule`; the mock's moves under it | asked for |
| Site files | `schedule.html`, `page-schedule.js`, `schedule.css`, `schedule-link.js`, `schedule-merge.js`, `site/mock/schedule.mjs`, `schedule.test.mjs` | follow the address |
| Python | `marathon_schedule_page.py` (pure) and `api/tools/marathon_schedule_page.py` | "schedule" alone already means the SOURCE's schedule here (`schedule_url`, `marathon.schedule_changed`, the card's *Schedule…*), and "tracker" already means a source that moves its own times (`the GDQ tracker`, `from: tracker`) — `_page` says which schedule this is |
| Keys | `marathon_tracker_refresh_seconds`, `marathon_controls_tracker` | the page's name; no existing key uses "tracker" |
| The mock's kinds | `web.marathon.tracker_*` | mock only, never written by the bot |
| CSS classes | `rs-*` kept | never shown to a person; renaming 120 lines of selectors buys nothing |

### What is still prototype-only

Every move but Started / Finished now; the undo book; `staff_at` and staff estimates; `from: staff`; the editable
kind; the mock's `web.marathon.tracker_*` kinds. The mock keeps all of it so marathon 60 still plays.
`contract.json` no longer lists the five mock-only POST routes or the nine mock-only kinds — the bot does not
answer them — and `schedule.test.mjs` walks every one of them against the mock instead.

## Deviations — live, read-only 2026-10-03

1. **`start_at` is the real start when one is known**, not always `scheduled_at`. For a clock-kept schedule they
   are the same moment (the re-time writes it). For a tracker they differ, and a row tagged *seen on stream*
   beside the tracker's time would be false.
2. **An eighth tag, `held`** (above), rather than guessing `follows`.
3. **`kind` is `tracker` / `clock_kept`**, not the prototype's `editable` / `read_only`: the brief asked for the
   kind of source, and `editable` is its own key. The mock was changed to match.
4. **The BaF mark is the People card's rule, not `is_ours`** (above). So a marathon can show a ✦BaF host on a row
   for which *What the bot posts next* lists nothing for that run alone — the host BLOCK's posts are listed.
   ⚠️ On a tracker, a matched COMMENTATOR is not marked BaF here, yet the tick still reminds for them
   (`commentators_count` is on for every source but Hotfix) and the post is listed, worded "runs".
5. **`can.start` is true on a DONE run and `can.finish` on an UPCOMING one**, because that is what the existing
   routes allow. The page keeps the obvious move on the row (*Finished now* on the live run, *Started now* on an
   upcoming one) and folds the other two behind **More…** as *Mark live again* and *Mark done*.
6. **Days:** more than four hours with nothing on starts a new day (the prototype's rule), and a block longer than
   24 hours — a marathon that never stops — is split by calendar date in `default_timezone`. Deviation 5 of the
   prototype (one rule with `marathon_signals.chains`) is NOT done: chains is a re-timing rule and splits at any
   gap over the setup reach, which would make a day of every break.
7. **A tracker's header says *Following the tracker*** while nothing has started, not *On time* (above). The
   mock's tracker sheets were changed to match.
8. **`moves` is not in `contract.json`'s row checks.** Both checkers fail an empty list, and a marathon with no
   re-time, no mark and no read change has none. Its row shape is proved in `tests/test_marathon_schedule_page.py`.
9. **The page's own sentences are constants in `page-schedule.js`**, as on every other page; the one string the
   BOT posts (the link button) is a key.
10. **No clean `/schedule` path** (above).
