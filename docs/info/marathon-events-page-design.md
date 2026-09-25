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
>
> 🔨 **2026-09-25 — BUILT on branch `marathon-events-page` (§A–§F), NOT merged, NOT deployed.** Schema 62, registry
> 469, commands 33, pages 22, routes 237; 23 deviations (⚠️ 1: two columns; ⚠️ 2: the PUT path never moved a scheduled
> event — a new helper does) and *What was NOT verified* at the foot.

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

*(written by the build agent, 2026-09-25, branch `marathon-events-page` off `main` `ed52ffeb`. Schema **61 → 62**,
registry keys **468 → 469** (+2, −1), top-level commands **34 → 33**, hidden-when-off rows **17 → 16**, pages
**23 → 22**, routes **235 → 237** (`check.mjs`: *22 pages, 237 routes*), log kinds **+6** bare (`event_made`,
`event_redated`, `event_unlinked`, `event_cancelled` routine; `event_make_failed`, `scheduled_move_failed` important by
their suffix). Cogs and log features unchanged.)*

**The three "pick, say which":** (a) **settings** — two sections, the events one titled *Settings* exactly as before
and a second *Marathon settings*: `namespaceSettings` draws one section per namespace and has no two-group form;
(b) **logs** — two sections, *Events log* and *Marathons log* (`logsSection` takes one feature; widening it would
touch every page); (c) **`where_kind`** — `other` (`events.WHERE_OTHER`), the raid-train kind, with the URL in
`location`, so **Spotlight this stream** reads it the same way.

1. ⚠️ **Two columns, not one: `marathons.event_id` AND `marathons.event_wanted INTEGER NOT NULL DEFAULT 0`.** "Box on,
   schedule unpublished" and "box off" are the same `event_id IS NULL`; the first dated read must know which. A
   sentinel value in the link column was the alternative and was rejected. Pre-62 rows read `0`: nothing is made for
   a marathon already on the list until staff press **Make an event now**.
2. **The re-date is `update_event` (the function `PUT /api/events/{id}` calls) plus a NEW `events.move_scheduled_event`.**
   ⚠️ §B said the PUT path "already moves the Discord scheduled event" — it does not: the route answers
   `SCHEDULED_STALE` (*"nothing here edits one that was already made"*). The new helper edits `start_time`/`end_time`,
   answers `moved`/`none`/`test_mode`/`failed: …` and logs nothing (§E: no new `event.*` kinds). The PUT route is
   unchanged. Title, description and Where are re-written as the EVENT holds them, so a staff edit survives.
3. **A failed move is its own IMPORTANT row, `marathon.scheduled_move_failed`** (checklist 2); `marathon.event_redated`
   carries `scheduled` either way (`test_mode` under the guard).
4. **A refused automatic proposal is `marathon.event_make_failed`** (IMPORTANT) and clears the wish, so a tick never
   re-files a cancelled row on every read. A staff press that is refused says why in words (the events module's own
   sentence, e.g. no review category) and also clears the wish.
5. **Who proposes it:** the presser; on the tick, the member who added the marathon; else `guild.me`. Nobody at all is
   refused in words (*nobody is left to propose it as…*) — a review room's overwrites need a member, never an int.
6. **Marathons… is drawn for staff always and for members while `marathon_mode` is not `off`** (the old `/marathon` hid
   when off; staff need the door to reach the feature). ⚠️ `/event` itself still hides when `events_mode` is off, and
   Marathons… goes with it.
7. **`marathon_mode` stays in the `/settings` mode block** as a hand-added row naming `/event` (the block is
   `HIDDEN_WHEN_OFF` + hand-added rows; 16 + 4 = 20, unchanged). `back_on_options` now lists only
   `HIDDEN_WHEN_OFF` keys — otherwise hiding `/event` would ALSO offer *Marathons — turn it on*, which turns on the
   wrong feature.
8. **`FEATURES_WITHOUT_A_COMMAND` is unchanged** — the logs-door guard is an AST walk for `send_logs(…, "marathon")`,
   which the sub-panel's Logs button still is. `LOG_LEVEL_COMMANDS['marathon']` = `event`, so the key's help reads
   *`/event` ▸ **Logs*** — one hop short of the truth (it is `/event` ▸ **Marathons…** ▸ **Logs**); the guard pins that
   exact form, so it was left.
9. **No Settings button on the sub-panel** (the old `/marathon` had none either); the namespace is reachable as ever
   through `/settings` ▸ *A setting group…* ▸ Marathons and the Events page's *Marathon settings*.
10. **Where:** the marathon channel's `https://twitch.tv/<login>`, else the schedule PAGE (`gamesdonequick.com/schedule/
    <id>`) rather than the raw `schedule_url`, which may be a tracker link. **`{channel}`** is `marathon_channel_id`,
    else the go-live channel (the board's own home), else blank.
11. **Only `pending` / `approved` events are re-dated or called off.** `live`, `done`, `denied` and `cancelled` are left
    with the link kept; the drawer says the status.
12. **`marathon_mode = shadow` does not stop the proposal.** It lands in the STAFF review (events has its own mode), and
    only a staff Add or press asks for one. `off` stops the tick, so a waiting marathon simply waits.
13. **Unlink also clears a waiting wish** (*… no longer waits to make an event*); with neither it is refused in words
    (`no_event`, 409). **Make an event now** on a linked marathon is refused `event_exists`, naming the event.
14. **The `/event` card's marathon line is appended to the card's description**, not a field; the events API carries
    `marathon: {id, name, line}` on EVERY event answer (list, detail, approve, deny, edit, cancel, forum, spotlight).
15. **The Add modal's fifth field** is free text: blank = the key's default, `yes`/`no` (and `y`/`true`/`on`/`1`…),
    anything else refused in words with nothing added. Pre-filled from `marathon_makes_event`.
16. **`makes_event` on `GET /api/marathons`** — the page's Add box default, so the section need not read the settings.
17. **The mock:** AGDQ 2027 (1) carries event **#5, approved** (dated from its schedule), so the Queue's default
    *waiting for a decision* view does NOT list it — **Open event #5** in its drawer, or *Show: approved*. Adding a
    marathon with the box ticked files a PENDING event there. `check.mjs` gains `marathon_bare_id` (3, GDQx — no dates,
    so *waiting*) and `marathon_waiting_id` (1 — Unlink reaches #5); the pytest contract seed adds a waiting GDQx row.
18. **`CANCEL_WHY['marathon_removed']`** — the requester's DM line is a constant beside the others (they are all
    constants), not a settings key. Flagged against the every-word-editable rule.
19. **Guides seed untouched:** there never was a `/marathon` guide row (`marathon-schedule` Deviation 20).
    `guides.FEATURE_PATHS['marathon']` now names `events.html` and `marathons-section.js`.
20. **`navMarathon` removed** from `icons.js`; the section heading draws no icon.
21. **The existing marathon cog tests set `marathon_makes_event` off in their fixture**, so the earlier builds' tests do
    not grow an event; the new tests pass `make_event=True` or read the key on purpose.
22. **Sweep rows `ME-a` … `ME-d`**, and `MS-a`, `MS-e`, `MN-a`, `MN-d`, `MN-e` re-pointed at `events.html` /
    `/event` ▸ Marathons….
23. **Commits:** the page move and the nav/pages/links sweep landed as ONE commit (`e3ddaa45`); the mock's two new keys
    rode with the schema commit.

## What was NOT verified

- ⚠️ **Nothing met Discord.** The Marathons… sub-panel, its Back, the card's Event line and moves, the modal's fifth
  field, the `/event` card's marathon line and — most of all — **`ScheduledEvent.edit(start_time=…, end_time=…)`** ran
  only against fakes. An ACTIVE Discord event cannot change its start; that case would land as
  `marathon.scheduled_move_failed`, by reasoning, not by trial.
- **The real `propose_from`** ran only in the API route tests (the web fixture's fake guild, events category set);
  the cog tests stand a recording `propose_from` in. No real review room or forum post was made.
- **The tick-driven "first dated read makes the event"** was driven by a fake schedule client and `cog.refresh`, never a
  real minute loop or a real GDQ publish.
- **Schema 62** was proven on a fresh file and a file downgraded to 61 (`tests/storage/test_db.py`), not on the live
  volume.
- **The page was rendered once**, `chrome-headless-shell` 149.0.7827.22 over raw CDP against the mock on port 8795:
  `events.html#marathon-1` opened AGDQ 2027's drawer (cards *Event · Runs · Who is who · The channel*, Event reading
  *APPROVED Event #5 — approved* with **Open event #5** / **Unlink**); the section order was *Queue · Marathons ·
  Settings · Marathon settings · Events log · Marathons log*; the nav had no Marathons row; **Open event #5** opened
  the detail with *Marathon: AGDQ 2027 — 3 run(s) of ours*; **Add a marathon** showed *Also make it an event*
  ticked. **Zero console errors.** NOT clicked in the browser: Unlink, Make an event now, the Add submit (the add
  was exercised against the mock with curl: a pending #7 with its marathon line), the detail card's link back, a phone
  width.
- **The old address answering 404 on Fly**, and whether a Discord scheduled event's description renders `<#id>` as a
  channel, were not seen.
