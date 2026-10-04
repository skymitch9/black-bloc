# Schedule viewer — a run sheet per marathon, with live staff re-timing

> **Audience:** the owner (to agree the design), then the build agent. **Status:** TRACKED.
> 📐 **DESIGN — NOT AGREED, NOTHING BUILT.** Every item under *Open decisions* is the owner's.
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

None yet — nothing is built.
