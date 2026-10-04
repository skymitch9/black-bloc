# Schedule viewer — a run sheet per marathon, with live staff re-timing

> **Audience:** the owner (to agree the design), then the build agent. **Status:** TRACKED.
> 📐 **DESIGN — NOT AGREED, NOTHING BUILT ON THE BOT.** Every item under *Open decisions* is the owner's.
> A local page on the mock exists to react to (branch `runsheet-proto`, 2026-10-03) — see *Prototype 2026-10-03* at the end.
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
