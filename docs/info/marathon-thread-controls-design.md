# Marathon thread controls — one pinned message in each tracked marathon's thread for its events and its spotlight

> **Audience:** the conductor, reviewers, and the next session touching marathon threads, event modes or the marathon
> spotlight. **Status:** TRACKED · 🔨 **BUILT on branch `marathon-thread-controls` (off `main` `28ad1e1c`), NOT merged,
> NOT deployed** — it ships with the merged, undeployed `marathon-thread-move` as v177. Schema **72 → 73**, registry keys
> **560 → 574**, routes unchanged (**264**), three new log kinds, deviations below.
> **Last verified: 2026-09-26** — against the branch's own code by the tests
> (`tests/cogs/content/test_marathon_thread_controls.py`, `tests/test_marathon_thread_controls.py`, the schema-73 test in
> `tests/storage/test_db.py`), the whole suite, and `check.mjs` on a worktree mock (`MOCK_PORT=8816`: *22 pages, 264
> routes, all keys present*). ⚠️ **NOT checked:** anything against Discord (the message, the pin, the buttons in a real
> client, a forum-post thread), the live database and its migration, the live marathons and channel rows; the bot was
> never run and nothing was rendered in a browser (there is no site surface). Secret NAMES only.

## The asks, verbatim (owner, 2026-09-26 19:3x–19:4x Phoenix)

1. *"How do we make a marathon generate events for the whole marathon and for our runners? This should have separate
   controls in the spawned thread for generating those events"*
2. *"Also need a start spotlight button in that same thread"*

**The answer to the question in ask 1** is the event mode that already exists (`marathon-event-modes-design.md`):
`marathon` makes one event for the whole marathon, `runs` one per BaF run (kept in step with the schedule), `both`
both. This build puts its two halves on two buttons inside the thread.

## As built

**The message.** One per tracked marathon's thread, posted by `cogs/content/marathon_thread_controls.py:post_controls`
right after the thread's opening line and **pinned**. Its id is `marathons.controls_message_id` (schema 73 — Deviation 1),
so every later render is an edit in place. It is posted:
- when the thread is made — `marathon_inbox.py:new_thread` is the one place a marathon thread is made, so this covers
  **Track**, a thread **made again** after a person deleted it, and the **thread-move** path (the new thread gets its own
  message; the old one stays in the archived thread);
- once for an **already-tracked** marathon whose thread has none — the minute tick (`sync_controls`, under the marathon
  lock) sees `controls_message_id` empty and posts. That is the v177 backfill for the live tracked marathons, and the
  same path re-posts a message a person deleted (the edit answers NotFound → `marathon.controls_lost`, the id is
  cleared, the same tick posts a new one).

**Three persistent buttons** (`ControlButton`, a `DynamicItem` registered in `Marathons.cog_load` beside the inbox
buttons; custom id `marathon:controls:{id}:{event|runs|spotlight}:{on|off}`, so they answer after a restart). Each
label is a key and reads the CURRENT state and the move; each button carries the TARGET in its custom id, so a label
that has not caught up yet can never do the opposite (Deviation 3):

| Button | Labels (keys) | A press |
|---|---|---|
| **Marathon event** | *Marathon event: on · turn off* / *…: off · turn on* | moves the marathon half of `event_mode` and writes the result through `cogs/content/marathon_events.py:set_event_mode` — the drawer's and the `/event` select's writer — so the event is made or called off exactly as from there |
| **BaF run events** | *BaF run events: on · turn off* / *…: off · turn on* | the runs half, the same way (off+off = none, on+off = marathon, off+on = runs, on+on = both — `black_bloc/marathon_thread_controls.py:wanted_mode`) |
| **Spotlight** | *Spotlight: on · stop* / *Spotlight: off · start* / *Spotlight: kept (permanent)* / *Spotlight: no channel* (greyed out) | below |

**Spotlight: start** (`start_spotlight`): refused in words when the marathon has no channel row, or no span still ahead
(`marathon_controls_no_end` — there is no end to hold it until); answers *already spotlit* when the row is on. Otherwise:
a marathon whose follow was **off** is set back to **follow** through `set_spotlight_mode` (whose follow may itself turn
the row on when the marathon is in reach); if the row is still off, it is turned on NOW through
`cogs/content/spotlight.py:changed_spotlight` — the write the `/golive` card's `set_spotlight` and the Go-live PATCH
both reach — with `spotlight = 1`, `expires_at` = span end + `marathon_spotlight_tail_minutes`, and
`spotlit_by_marathon` = this marathon. From then on it is a held spotlight like any the follow sets: the expiry sweep's
`settle_held` extends it if the schedule grows and lifts it at span end + tail.

**Spotlight: stop** (`stop_spotlight`): a **kept** row (spotlit, no end — GDQ) is refused in words
(`marathon_controls_kept_refused`) and never turned off here. Otherwise the row goes off through `set_spotlight` +
`after_staff_dim` — the exact pair `run_spotlight_move` (`/golive` ▸ Channels… *Spotlight off*) calls — so a following
marathon in reach gets `spotlight_mode = off` (v174), and then this marathon's `spotlight_mode` is set **off** through
`set_spotlight_mode` if it is not already (Deviation 4).

**Every press** is staff-gated by `still_staff` (the standing worded refusal), defers, answers ephemerally in the
writer's own sentence, and re-renders the message.

**Re-render from any door** (`refresh_controls`, edit only, never posts): the canonical writers call it —
`set_event_mode`, `make_event_now` and `unlink_the_event` (the two other `event_mode` writers staff reach),
`set_spotlight_mode`, `after_staff_dim`, `follow_spotlight`, `lift` (held rows), and `changed_spotlight` (every Go-live
and `/golive` write to a channel row, for every marathon on that row). What it would show — the help line, the three
controls and their labels — is compared with what was last shown (in memory, per marathon); equal costs no Discord call.
The minute tick runs the same compare, which also catches the writers that are not hooked (a stored-wish drop
`stop_waiting`, the expiry sweep's purge) within a minute, and a staff edit to a label key (the every-word rule: a posted
copy re-renders when its words change).

**The line** under the message is `marathon_controls_help` (*Staff: these buttons set **{marathon}**'s events and its
channel's spotlight at once. Each one says what is on now and what a press does.*), plus
`marathon_controls_no_channel` when the marathon has no channel row.

**Keys (fourteen, Marathons group, registry + mock row + label):** `marathon_controls_help`,
`_event_on` / `_event_off`, `_runs_on` / `_runs_off`, `_spotlight_on` / `_spotlight_off` / `_spotlight_kept` /
`_spotlight_none`, `_no_channel`, `_kept_refused`, `_no_end`, `_started_said`, `_already_on`.

**Log kinds:** routine `marathon.controls_posted` (`marathon_id`, `name`, `thread_id`, `message_id`, `pinned`),
routine `marathon.controls_lost`, `marathon.controls_failed` (IMPORTANT by suffix; `step: post | pin`). A start logs
through the canonical write: `golive.spotlight_updated` with `spotlight`, `expires_at` and `spotlit_by_marathon`.

## Deviations

1. **A column, `marathons.controls_message_id INTEGER`** (schema **72 → 73**, `ADDED_COLUMNS`, mirrored to
   `marathons_archive` at boot, NULL for every row). No existing field fits: the marathon row has no JSON cell, and
   `marathon_inbox` is keyed by home, not by marathon. The alternative — finding the message in the thread's pins on
   every boot — costs a Discord read per tracked marathon and would post a duplicate whenever staff unpin it. The brief's
   *"id compare only"* backfill needs a stored id. Additive; no backfill; the first tick after the deploy posts one
   message into each tracked marathon's thread.
2. **The help line sits ABOVE the buttons**, not under them: a classic Discord message draws its text first and its
   components after. The repo does not use Components V2 (`LayoutView`), and the fakes do not model it.
3. **Each button carries its target, not "toggle".** `…:event:on` always asks for the marathon half ON; pressed when it
   is already on (a stale label), `set_event_mode` answers *already makes…* and nothing changes.
4. **Stop always leaves the marathon's follow OFF.** `after_staff_dim` only sets it for a following marathon in reach
   (v174's rule for a Go-live Off); a press in THIS marathon's thread is about this marathon, so outside its reach the
   follow is set off too — otherwise the marathon would spotlight the channel again at its next span, against what
   staff just pressed. **Start** turns it back on.
5. **Start on an already-spotlit row changes nothing** (*already spotlit*) — it does not take over a staff-dated
   spotlight as a held one. The label reads *on · stop* in that state anyway.
6. **Start needs a span still ahead.** A marathon with no run times, or one whose last run plus the tail is past, is
   refused in words (*no end to hold the spotlight until*) and pointed at Go-live, where a staff spotlight has staff
   dates. Without an end a "held" spotlight would never be lifted.
7. **Start does not touch the row's `starts_at`.** A row with a future start stays scheduled (that field gates the
   channel's announcements, v174 Deviation 2).
8. **Two quick presses on different halves by two people in the same instant** can lose one: the new mode is computed
   from the row just before `set_event_mode` takes the marathon lock. Sequential presses are exact; the label shows the
   result either way.
9. **A thread that auto-archived is re-opened to edit its message** (an archived thread's messages cannot be edited);
   only a TRACKED marathon's message is ever edited. An untracked marathon's message stays as it was in its archived
   thread; its buttons still answer (they act by marathon id) and Track again re-renders it on the next tick.
10. **The move path leaves the old message and its pin in the archived old thread** (the old thread is archived by
    `move_thread` after the new one is made, and nothing edits it again); the new thread gets a fresh pinned message.
11. **Not hooked, caught by the tick within a minute:** `stop_waiting` (a marathon-event wish the review refused drops
    the marathon half), the expiry sweep's purge of an unheld row, a row removed on Go-live, a channel change on the
    marathon. Each is a writer that runs inside the tick or has no guild in hand.
12. **The shadow home gets the message too** — the thread is there, and the message posts nothing to members.
13. **Button styles:** on = green (success), off = grey, kept = blurple, no channel = greyed out. Styles are not keys
    (not words).
14. **`press` (`cogs/content/marathon_thread_controls.py`) is the one door**; there is no site or `/event` twin — the
    same moves already exist there (the Event select, the Spotlight card and *Follow the schedule*), and every one of
    them re-renders this message.

## What was NOT verified

- ⚠️ **Nothing met Discord.** The post, the pin (a forum-post thread's pin in particular), the persistent buttons in a real
  client and after a real restart, the ephemeral answers, and editing a message in a thread that had auto-archived were
  exercised against the suite's fakes only.
- ⚠️ **The live migration (schema 73) has not run**, and the live tracked marathons were not read: how many messages the
  first tick after v177 posts is one per tracked marathon with a thread in the current home — the number is the
  conductor's to read.
- **The run-events half** was tested through the real `set_event_mode` with `events_create_scheduled` off and the review
  faked (`proposals`), as the event-mode tests do; no event was approved against Discord.
- **The spotlight start's pin of a live stream** goes through `changed_spotlight` → `settle_open_session`, covered by the
  spotlight tests, not re-tested here with an open session.
- **No site change**, so nothing was rendered; the Settings page listing the fourteen keys was checked by `check.mjs` and
  the registry tests only.
