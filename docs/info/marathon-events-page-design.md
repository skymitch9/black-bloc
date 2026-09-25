# Marathons share the Events page — a marathon is an event, so it lives where events live

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-25 13:3x Phoenix),
> dispatched to Opus as branch `marathon-events-page`** off `main` `054515c3` (v163 live + three merged, undeployed
> builds: `spotlight-ping-windows`, `marathon-schedule`, `marathon-next-event`). **Last verified: 2026-09-25 13:2x**
> against that `main`: `site/public/assets/page-events.js` — `load()` `:272` (one *Queue* section from `GET
> /api/events?status=`, an optional `#detail` section for `state.open`, `namespaceSettings('events')`,
> `logsSection('events')`; 329 lines), `page-marathons.js` (546 lines, the list / drawer / Add form / Next up card /
> §G moves — the content that MOVES); `shell.js:GROUPS` `:36` (the *Marathons* nav row, `feature: 'marathon'`);
> `logkinds.py` `FEATURE_PAGES['marathon'] = 'marathons.html'` `:144`; `cogs/content/raidtrain.py:make_event_for`
> `:678` — **the precedent**: a train's event goes through `cogs/community/events.py:propose_from` `:349` like any
> proposal, `set_event(db, train_id, event_id)` links it, `event_fields(bot, guild, train, slots)` builds the draft;
> `events.py:create_event` `:968` (`title, description, where, starts_at, finishes_at`); `storage/db.py` `events`
> `:250` (`starts_at`, `ends_at`, `location`, `where_kind`, `scheduled_event_id`, `status`); `api/tools/events.py` —
> `PUT /{event_id}` `:189` (the edit path that also moves the Discord scheduled event; reuse its function), `POST
> /{event_id}/cancel` `:276`; `cogs/community/events.py` — `EventView` `:446` (the `/event` root panel), `RoomsButton`
> `:1494` / `ScheduledButton` `:1423` (the sub-panel buttons a **Marathons…** button sits beside); `tests/test_bot.py`
> `TOP_LEVEL_NOW = 34` `:13`, the hidden-when-off list (17), `logkinds.FEATURES_WITHOUT_A_COMMAND = ("guides",)`.
> Schema is **61**; this build takes **62**. ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-25 12:5x Phoenix)

*"i think marathons and events can share a page since a marathon will be an event"*

**Read as three things, all built here:** (1) ONE page — the Marathons page's content becomes a section of the Events
page and `marathons.html` goes; (2) a marathon IS an event — adding one also makes an Events row, kept in step with
the schedule's dates; (3) ONE command — `/marathon` folds into the `/event` panel as **Marathons…**, the way `/twitch`
folded into `/golive` (owner rule: minimise slash commands).

## A. One page

- `marathons.html` is **deleted** and `page-marathons.js` becomes **`marathons-section.js`**, exporting
  `marathonsSection({ say, open })` — the same list, drawer, Add form, Next up strip and card, and the §G moves,
  rendered as ONE `section('Marathons', …)` with its own count. `page-events.js:load()` appends it after the Queue (and
  the `#detail` section when one is open), before the settings. Nothing in the marathon section changes behaviour;
  it changes address.
- Deep links: `events.html#marathon-<id>` opens that marathon's drawer (the section reads `location.hash` the way the
  page did); the staff notice, the board's page link, the Logs page's row links and `FEATURE_PAGES['marathon']` all
  point at `events.html` now. `grep -rn "marathons.html"` across `black_bloc/`, `site/`, `tests/` and `docs/` must
  come back empty except history (`DONE.md`, the two marathon designs' record lines, `deploys.log`).
- The Events page's settings area shows BOTH namespaces (`events` then `marathon`, two foldouts under one *Settings*
  heading, or one foldout with two groups — the builder picks what the page's helper supports and says which) and
  its logs section shows both features' rows (`logsSection` takes one feature today; give it a list, or render two
  sections titled *Events log* / *Marathons log* — pick, say which).
- `shell.js:GROUPS` loses the *Marathons* row; the Events row's `feature` stays `events` (the nav dot is the events
  feature's). `site/mock/check.mjs` and `docs/access/site.md` go 23 → **22** pages. The `navMarathon` icon may stay in
  `ui.js` if the section's heading uses it; otherwise remove it.
- KI-36-style guard: whatever fixture asserts the page count or the page list (`check.mjs`, `test_contract`) is
  re-measured, not hand-adjusted blind.

## B. A marathon is an event

- **`marathons.event_id INTEGER`** (`ADDED_COLUMNS`, schema 61 → **62**), NULL until an event is made; the events
  row is NOT widened (the raid-train precedent keeps the pointer on the train).
- **Adding a marathon makes an event** when `marathon_makes_event` (bool, **true**) and the Add form's *Also make it
  an event* box (default from the key; site form + the `/event` ▸ Marathons… Add modal's fifth field *Make it an
  event? yes/no*) is on: the SAME `propose_from` path a raid train uses — through the events review, never around it
  (the reviewer is staff; staff added the marathon; one press approves it — and the review is where the Discord
  scheduled event, the announcement and the room come from, so skipping it would skip those too). The draft's
  fields: title = the marathon's name; description from `marathon_event_description_template` (text: *{marathon} —
  read from the GDQ schedule. Our runs are boarded in {channel}.*, `{channel}` the marathon channel mention);
  Where = the marathon's channel URL (`https://twitch.tv/<login>`) when it has one, else the schedule URL; starts /
  ends = the schedule's `starts_at` / `ends_at` — **so an unpublished schedule (AGDQ 2027 today) makes NO event
  yet**: the event is made on the first fetch that yields dates, and the drawer says *Event: waiting for the schedule*.
  `marathon.event_made` (routine) with both ids.
- **Kept in step.** When a fetch moves the marathon's `starts_at` or `ends_at`, the linked event (status `pending`
  or `approved`) is re-dated through the events module's edit function — the one `PUT /api/events/{id}` uses — which
  already moves the Discord scheduled event; `marathon.event_redated` (routine, old → new). A `denied` or `cancelled`
  event is left alone and the link stays (the drawer says so).
- **Staff final say, both ways.** The marathon drawer's *Event* line: *Event #12 — approved · opens it* with **Unlink**
  (clears `event_id`, touches the event not at all) and, when there is none, **Make an event now** (the same path, for a
  marathon added with the box off, or after an unlink). The Events page's detail card and `/event`'s card show
  *Marathon: AGDQ 2027 — 3 runs of ours* linking back. Removing a marathon **cancels its pending/approved event with
  the reason `marathon_removed`** through the existing cancel path (that is the one move that keeps the server's event
  list honest) and logs `marathon.event_cancelled`; pausing does nothing to the event. Cancelling the event from the
  events side leaves the marathon and its link (the drawer reads *Event #12 — cancelled*).
- Event side, `where_kind`: whatever value `events.where_link` gives a `twitch.tv` URL today (`link`?) — the builder
  reads `events.py` and uses the real kind, so **Spotlight this stream** on the event card keeps working for it (it
  would offer to spotlight the marathon channel, which is usually already a channel row — the existing refusal in
  words covers that).

## C. One command

- `/marathon` is **retired**: the `app_commands.command` goes, `TOP_LEVEL_NOW` 34 → **33**, the hidden-when-off
  count 17 → **16**, the guides seed row for `/marathon` goes (its screenshots with it; `tests/test_guides.py` guards).
- `/event`'s root card gains **Marathons…** — visible to everyone (members get what `/marathon`'s member root gave:
  *Ours next* and *My runs*; staff get the list, the marathon pick and every staff move, *Next up…*, *Re-read
  every…*, the run pick with its four moves) — a sub-panel exactly like `RoomsButton` / `ScheduledButton` open
  theirs, with **Back**. Everything the old panel did, unchanged, one level deeper. The `Logs` / `Settings` buttons on
  the marathon sub-panel keep the `marathon` feature's log kinds and the `marathon` namespace reachable, so the
  feature-has-a-logs-door guard in `tests/test_bot.py` is satisfied by the sub-panel's button; if that guard counts
  TOP-LEVEL commands only, add `marathon` to `FEATURES_WITHOUT_A_COMMAND` and say so in Deviations.
- `marathon_panel_minutes` is dropped in favour of `event_panel_minutes` (one panel, one lifetime): the registry key
  goes, its mock row and label go, the count guards move.

## D. Keys — two new, one gone

`marathon_makes_event` (bool, true), `marathon_event_description_template` (text, above; validator refuses an
unknown `{…}`); `marathon_panel_minutes` retired. Registry + mock + labels + the Marathons settings group. Keys 468 → 469.

## E. Logging

`marathon.event_made`, `marathon.event_redated`, `marathon.event_unlinked`, `marathon.event_cancelled` (all routine)
under the existing `marathon` feature; the events side logs its own `event.*` rows as any proposal / edit / cancel does
(no new kinds there).

## F. Tests, docs, gate

`tests/cogs/content/test_marathon.py` (add with the box on → one pending event with the schedule's dates, title,
Where and description; with the box off → none; an unpublished schedule → no event until the first dated fetch; a
fetch that moves the dates re-dates the event and moves the scheduled event; a denied event is left alone; Unlink;
Make an event now; remove → cancel with the reason; pause → nothing), `tests/cogs/community/test_events.py` (the
Marathons… button opens the sub-panel; the member view; the staff view; the card's marathon line), `tests/api/tools/
test_marathons.py` (`make_event` on POST, the unlink / make-now routes, `event` on the row), `tests/api/tools/
test_events.py` (the row's `marathon` field), `tests/api/test_contract.py`, `tests/storage/test_db.py` (62),
`tests/test_bot.py` (33; 16), the key / kind / page guards, the guides seed test, `check.mjs` (22 pages). Both
`pytest -n 8` orders, `ruff`, ES parse, node tests, a mock port of the builder's own. Docs: `code-notes.md`; this
doc's foot; `architecture.md` (schema 62, the retired command, the page); `docs/info/README.md` (one row);
`docs/access/site.md` (22 pages); `marathon-schedule-design.md` and `marathon-next-event-design.md` one dated line
each (the page and command moved); `sweeps.md` rows `ME-a…` (a: the Events page shows the Marathons section with
the seeded rows and the Next up strip; b: adding a marathon with the box on makes a pending event in the queue above
it; c: `/event` ▸ Marathons… shows *Ours next*; d: `marathons.html` is gone and the staff notice's link opens the
events page on the marathon). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`. ⚠️ Migrate before
deploy: one column through `ADDED_COLUMNS`.

## Deviations

*(the build agent writes this)*

## What was NOT verified

*(the build agent writes this)*
