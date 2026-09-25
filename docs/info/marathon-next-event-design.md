# The next GDQ event — suggested when a marathon ends, added by staff, never by itself

> 🔨 **2026-09-25 — generalised by `marathon-feeds` (NOT merged):** a GDQ feed now reads the same events list every 6 h and ADDS new events by default (or suggests them with this build's record-and-notice shape), so an over GDQ marathon's next event is usually on the list already — this suggestion then records it as added and posts no notice (Deviation 7 here). See [`marathon-feeds-design.md`](marathon-feeds-design.md).

> ✅ **2026-09-25 — LIVE as v164 14:16** (release commit `7787b10c`, [`deploys.log`](../deploys.log)): boot log `database: added marathons.suggested_next` at 21:15:56Z (this design's schema 61); `database ready`, `synced 33 app commands`, `logged in as Black_Bloc` 21:16:01Z, no Traceback; `/health` ready=true 67 ms. Nothing has met Discord by hand — the sweeps are the owner's; the live site was not opened in a browser.

> 🔨 **2026-09-25 — MOVED by branch `marathon-events-page` (NOT merged):** the Marathons page is now the Marathons section of `events.html` (`marathons.html` deleted, `page-marathons.js` → `marathons-section.js`, deep link `events.html#marathon-<id>`), `/marathon` is retired into `/event` ▸ **Marathons…** (`marathon_panel_minutes` → `event_panel_minutes`), and a marathon now makes an event — see [`marathon-events-page-design.md`](marathon-events-page-design.md). Behaviour below is unchanged; only the address and the command moved.

> 🔨 **2026-09-25 — BUILT on branch `marathon-next-event` (§A–§G), NOT merged, NOT deployed.** Schema 61, registry
> 468, routes 235; 23 deviations (⚠️ 1: drafts are kept — every event ahead is a draft), the three header questions
> answered and *What was NOT verified* at the foot.

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-25 12:2x Phoenix)
> — dispatches to Opus as branch `marathon-next-event` AFTER `marathon-schedule` merges** (it extends that build's
> tables, routes, page and panel; read that design's `## Deviations` FIRST, because the names below are the design's
> and the build may have moved them). **Last verified: 2026-09-25 11:0x** — one live fetch: `GET
> https://tracker.gamesdonequick.com/tracker/api/v2/events/` answers `{count, next, previous, results[]}`, each event
> `{type, id, short, name, hashtag, datetime, timezone, locked, archived, draft, allow_donations, …}`; the two newest
> were **74 `AGDQ2027`** (*Awesome Games Done Quick 2027*) and **73 `halofest`**. ⚠️ Not verified: whether the list
> is ordered by id or by `datetime`, whether a future event carries `draft: true` until announced, and whether
> `datetime` is the first run's start or a doors-open moment — the builder reads the live list and records all three
> in Deviations. ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-25 12:0x Phoenix)

*"for the during marathon, especially for GDQ we should use the api to grab the next event and suggest that once the
marathon build ends."*

**Read as:** when a GDQ marathon is over, Black Bloc looks up the next GDQ event on the tracker and SUGGESTS it to
staff, so the next one is one press away instead of a URL hunt. Staff still decide (*staff get the final say*): a
suggestion is never a row until someone presses **Add it**.

## A. The model — one nullable pointer per marathon, and a suggestion that is not a row

`marathons` gains **`suggested_next TEXT`** (`ADDED_COLUMNS`, one schema bump from wherever `marathon-schedule` left
it): JSON `{event_id, short, name, datetime, url, found_at, dismissed_at, added_marathon_id}`, or NULL. It is written
ONCE per marathon at the moment it goes **over** (the state `marathon-schedule` gives a marathon one day after its
`ends_at`; if the build named it differently, use its name) and by **Look again** (below). A dismissed suggestion keeps
its record with `dismissed_at`, so the same event is never re-suggested to the same marathon; an added one keeps
`added_marathon_id`, which is the link the page draws.

**Finding it — `black_bloc/marathon_sources.py:next_gdq_event(events, after, now)`**, pure: from the events list,
drop `draft` and `archived` rows, keep those whose `datetime` is after `now`, sort by `datetime`, and return the
first whose `id` is not the marathon's own `source_ref`. The cog fetches the list through the same client the
schedule fetch uses (one page is enough — the list is small; follow `next` only if `count` exceeds the page). The
suggested schedule URL is the tracker form the reader already accepts (`https://tracker.gamesdonequick.com/tracker/
event/<id>`), so **Add it** is exactly `POST /api/marathons` with `name` = the event's `name`, that URL, and the
ending marathon's `spotlight_id` — nothing new to parse.

**Only GDQ.** A marathon whose `source` is not `gdq` never gets a suggestion (the other readers are parked); the page
says nothing for those rows.

## B. When it fires

On the tick that moves a `gdq` marathon to **over**: fetch the list, compute the suggestion, write `suggested_next`,
log `marathon.next_suggested` (**IMPORTANT** — it is the one row staff should see: `event`, `short`, `datetime`), and
post ONE staff notice (§C). No event ahead → write `{found_at, event_id: null}` and log `marathon.next_none`
(routine); **Look again** re-runs it by hand. A fetch failure logs `marathon.next_failed` (routine) and leaves
`suggested_next` NULL so the next boot's reconcile (one row per boot, `loops.Reconciler`) tries once more for every
over GDQ marathon that has no suggestion record. ⚠️ Never fire twice: the write of `suggested_next` and the post are
ordered record-first, and a NULL-after-failure is the only state that retries.

## C. Doors

**The site — the Marathons page.** An over GDQ marathon's row (and its drawer) carries a **Next up** card:
*AGDQ 2027 is over — the next GDQ event is **SGDQ 2027**, `<t:…:D>` (`{relative}`).* with **Add it** (→ `POST
/api/marathons` as §A; on success the card reads *Added — see SGDQ 2027 below* and links the new row), **Not this
one** (→ `PATCH /api/marathons/{id}` with `dismiss_next: true`; the card folds to one quiet line *Dismissed — Look
again*), and **Look again** (→ `POST /api/marathons/{id}/next`, which re-fetches and re-suggests, clearing a
dismissal). The page's list also gets a top strip when any suggestion is open: *1 marathon has a next event waiting*.
Contract + mock rows: *Halo Fest* (over) with an open suggestion of *AGDQ 2027*; one over marathon with a dismissed
one.

**Discord — the staff notice + `/marathon`.** The notice goes to the staff channel the requests / events reviews use
(`staff_channel_id` or whatever key `marathon-schedule` chose for its IMPORTANT posts — reuse, never a new channel
key): the same sentence as the card, with **Add it** / **Not this one** buttons (a persistent view keyed
`marathon:<id>:next:<event_id>`, staff-gated, both buttons edit the notice to its outcome and disable themselves —
KI-20 rules: survive a restart through the `DynamicItem` template the event card uses). `/marathon` ▸ the staff
half's marathon select gains **Next up…** on an over GDQ marathon, opening the same three moves. Shadow mode sends
the notice to the shadow home with the rehearsal note, `marathon.would_suggest_next`.

## D. Keys — four, namespace `marathon_`

`marathon_suggest_next` (bool, true — the whole feature's switch), `marathon_next_template` (text: *{marathon} is
over — the next GDQ event is **{next}**, {when} ({relative}). Add it?*), `marathon_next_none_template` (text: *{marathon}
is over and the GDQ tracker lists nothing ahead yet — Look again later.*), `marathon_next_added_template` (text:
*Added **{next}** — it will be read from {url}.*). Button labels are constants beside the marathon words. Registry +
mock + labels + `placeSettings` (the Marathons drawer) + the join fixture.

## E. Logging

`marathon.next_suggested` (IMPORTANT), `marathon.next_none`, `marathon.next_failed`, `marathon.next_added` (routine,
`by`, `via`, the new `marathon_id`), `marathon.next_dismissed` (routine), `marathon.would_suggest_next` (shadow). The
`marathon` feature already exists; no new chip.

## F. Tests, docs, gate

`tests/test_marathon_sources.py` (`next_gdq_event`: skips draft / archived / past / itself, picks the soonest, empty →
None; against a captured events-list fixture trimmed to ~6 rows under `tests/fixtures/marathon/`),
`tests/cogs/content/test_marathon.py` (over → one suggestion + one notice, never twice; failure → NULL and the boot
reconcile retries once; dismiss → no re-suggest of the same event; Look again after a dismissal suggests again; Add it
→ a new marathon row with the parent's channel and `added_marathon_id` set; the buttons are staff-gated; shadow →
the shadow home), `tests/api/tools/test_marathons.py` (`dismiss_next`, `POST …/next`, the refusals in words: not GDQ,
not over, nothing suggested), `tests/api/test_contract.py`, `tests/storage/test_db.py` (the bump), the key / kind
guards, the page join fixture, `check.mjs`. Both `pytest -n 8` orders, `ruff`, ES parse, node tests, a mock port of
the builder's own. Docs: `code-notes.md`; this doc's `## Deviations` + `## What was NOT verified`; `architecture.md`;
`docs/info/README.md` (one row); `marathon-schedule-design.md` one dated line at the top; `sweeps.md` rows `MN-a…`
(a: an over GDQ marathon shows Next up with the real next event; b: Add it makes the row and links it; c: Not this
one folds the card and the notice; d: Look again after a dismissal). NOT `TODO.md` / `DONE.md` / `deploys.log` /
`KNOWN_ISSUES.md`. ⚠️ Migrate before deploy: one column through `ADDED_COLUMNS`.

## G. Two leftovers from `marathon-schedule`, built here because they are the same surfaces

The `marathon-schedule` build flagged two gaps it did not close (its Deviations, 2026-09-25):

1. **A marathon's own `poll_minutes` has no door.** It is accepted by `PATCH /api/marathons/{id}` only. Checklist 33
   (configurable both ways) wants a control: on the Marathons page drawer a small *Re-read every N minutes — blank
   for the default* field beside Pause / Resume, and in `/marathon`'s staff half a **Re-read every…** modal on the
   picked marathon (one `TextInput`, blank clears it; bounds as the key's, refused in words).
2. **A `done` run has no move back.** Staff get the final say, and a run the title match marked done by mistake
   (a rerun in the title, a mis-scored game name) must be recoverable: **Mark it upcoming** on a `done` or `dropped`-
   then-back run (state → `upcoming`, `live_at` / `done_at` cleared, `reminders_sent` kept so nothing re-posts) and
   **Mark it live** (state → `live`, `live_because: staff`; shouts if it has not) on the page's run row and in
   `/marathon` on the run pick the **Shout it now** move already uses. Routes: `POST …/runs/{run_id}/upcoming`,
   `POST …/runs/{run_id}/live`. Log `marathon.run_reset` / `marathon.run_live` (`because: staff`).

## Deviations

*(written by the build agent, 2026-09-25, branch `marathon-next-event` off `main` `6bb49274`. Schema **60 → 61**,
registry keys **464 → 468**, routes **231 → 235** (`check.mjs`: *23 pages, 235 routes*), log kinds **+8** bare
(`next_suggested`, `would_suggest_next`, `next_none`, `next_failed`, `next_added`, `next_dismissed`,
`next_notice_failed`, `run_reset`; `run_live` gained a staff door). Cogs, pages and top-level commands unchanged.)*

**The three header questions, answered from the live list** (`GET …/api/v2/events/`, 2026-09-25 13:1x Phoenix, curl
AND the bot's own `ScheduleClient.events()`): **(1) ordering** — by `datetime`, newest first; ids are NOT monotonic
(`jrdq` 4 sits between `sgdq2011` 3 and `agdq2011` 5). `count: 70`, `next: null` — one page. **(2) `draft`** — every
event still ahead is `draft: true` (71 *Games Done Hitless* 2026-10-23, 72 *GDQx 2026*, 73 *Halo Fest*, 74 *AGDQ 2027*)
and every past one is `false`: draft means "announced, schedule not published". **(3) `datetime`** — the first run's
start: SGDQ 2026 (66) is `2026-07-05T12:30:00-04:00`, exactly run order 1's `starttime` in the committed runs fixture.

1. ⚠️ **`draft` events are NOT dropped** (§A said drop them). By answer (2), dropping drafts would suggest nothing, ever
   — the next event is always a draft when a marathon ends. Only `archived` rows are dropped. The fixture
   `tests/fixtures/marathon/gdq_events_list.json` is the live list trimmed to 74, 73, 72, 71, 69 and 68 (archived).
2. **"Over" is the shipped `mt.phase` OVER — `now > ends_at` on an ACTIVE marathon — not `ends_at` + one day.** The
   `marathon-schedule` build gives OVER at `ends_at`; one day after is only when its board comes down (`board_due_off`).
   A marathon whose schedule slips late may therefore be suggested at the old end; harmless, staff decide.
3. **Paused marathons get no automatic suggestion** (the tick returns before the suggestion for an inactive row, the
   "paused = nothing is read or posted" rule). **Look again**, the page card and the panel's **Next up…** work on any
   over GDQ marathon, paused or not (`mt.is_over` ignores `active`).
4. **`marathon_mode = off` suggests nothing automatically** — the tick does not run in `off`. The staff moves (Look
   again, Add it, Not this one) still work in `off` (staff final say); the notice is simply not posted.
5. **"The next boot's reconcile retries" is the tick itself**, which already runs through `loops.Reconciler` at
   `on_ready`: an in-memory `_next_tried` set means one lookup per marathon per process; a failure leaves NULL and only a
   new process tries again. No second reconcile row was added.
6. **"Next" means the soonest event ahead of NOW**, not ahead of the ending marathon (as §A reads). Measured today every
   GDQ marathon's next is 71 *Games Done Hitless*. Ties break on the id so the answer never flickers.
7. **An event already on the list** (a GDQ marathon with the same `source_ref`) is recorded as ADDED with that row's id,
   logged `marathon.next_suggested` with `already_on_list`, and gets NO notice. **Add it** on a stale suggestion does
   the same link instead of adding a twin. (The list's own `UNIQUE` is by URL, so `schedule/75` and
   `tracker/event/75` would otherwise both be addable.)
8. **A seventh kind, `marathon.next_notice_failed`** (IMPORTANT by the `_failed` suffix): checklist 2, a failed post
   must not share a kind with the dry run. The record is written first, so it stays open on the page.
9. **The notice goes to `staff_channel_id`.** There is no shared review channel: requests use
   `request_notify_channel_id` and events make rooms. Unset → one `next_notice_failed` row naming the key.
10. **Look again posts no notice** (staff are already looking at the page or the panel). If it lands on the same event
    while a notice is open, the notice ids carry over; any other old notice is folded (below).
11. **Notice outcomes, no fifth key:** added → `marathon_next_added_template`; dismissed or superseded → the original
    sentence struck through (`~~…~~`). The buttons stay on the message, disabled (not removed).
12. **Custom ids are `marathon:<id>:next:<event_id>:add|dismiss`** — two buttons need two ids; the design's key plus
    the action. A click whose event is no longer the waiting one is refused `suggestion_moved` in words.
13. **Add it on the site is `POST /api/marathons` with `{next_of, event_id}`**, not the page resending name / URL /
    channel: the server takes those from the record (and the ending marathon's `spotlight_id`, dropped if that channel
    row is gone) so ONE write makes the row and links it. The contract keeps one `POST /api/marathons` entry (its ids
    are method + path) with a second `read_by`; the `next_of` branch is covered by `tests/api/tools/test_marathons.py`.
14. ⚠️ **Add it leaves two rows**: `marathon.added` (from `create_marathon`, as any add) and `marathon.next_added`
    (§E). They are two events, not one event twice (checklist 34's case) — flagged for the reviewer anyway.
15. **§G staff hold.** A run with `live_because = staff` in `upcoming` or `live` is never closed or skipped by a title
    hit or a later schedule start (`mt.held`, two lines in `mt.advance`); only its own end + `marathon_late_grace_minutes`
    closes it. Without this the next minute's tick undoes the staff move whenever the title still matches another run.
    It also applies to runs **Shout it now** flipped live (the previous build already wrote `live_because = staff`).
16. **Mark it upcoming** clears `live_at` / `done_at`, keeps `reminders_sent`, AND sets `live_because = staff` (the
    hold marker). The clock still wins: a run whose whole slot + grace has passed is aged out again on the next tick
    (`run_skipped` if ours). Only `done` runs qualify — a `dropped` run is off the schedule (the next read would drop it
    again) and a dropped-then-back run already returns to `upcoming` by itself.
17. **Mark it live** logs the existing `marathon.run_live` (`because: staff`, `from`) for ANY run, not only ours (a staff
    write always leaves its row). It shouts only a run of ours with no shout yet; a shout already rewritten to the past
    tense is not rewritten back.
18. **`/marathon` had no run pick** — §G assumed **Shout it now** lived on one; it lived only on the page. Built: a
    run select on the card (ours, anything live, anything done in the last 12 h — the 25 nearest now) opening a run
    view with only the valid moves of **Shout it now / Mark it live / Mark done / Mark it upcoming**, plus **Back**.
19. **`PATCH poll_minutes: null` now clears** (it was silently ignored, `None` meant "not given"); the page sends null
    for blank. The panel's **Re-read every…** modal sends digits as a number and anything else as text, refused in the
    shipped `BAD_POLL` words.
20. **The page's Next up is a list column AND the drawer card** (a card per table row would not fit the table). The
    strip reads *N marathon(s) has/have a next event waiting*. **Mark it live** is drawn where `can_mark_live` and the
    run is not shoutable (Shout it now already covers that case).
21. **The mock's waiting suggestion is *Games Done Hitless* (71), not AGDQ 2027** — AGDQ 2027 is the mock's marathon 1,
    so Add it would be a duplicate. The mock gains a fourth marathon, *Flame Fatales 2026* (over, suggestion dismissed).
22. **Keys:** the four are in `MARATHON_SETTINGS` / `MARATHON_WORDS`, so the *Marathons* settings group and the page's
    own Settings foldout pick them up by namespace; there is no `placeSettings` drawer (the previous build's deviation
    14) and `golive-join.test.mjs` is untouched.
23. **Sweep rows `MN-a` … `MN-e`** — `e` is §G.

## What was NOT verified

- ⚠️ **Nothing met Discord.** The staff notice, its two persistent buttons, the fold edits, `/marathon`'s Next up / run
  views and the Re-read modal ran only against the suite's fakes. **KI-20 restart survival** is shown only by
  `NextButton.from_custom_id` rebuilding from a regex match of a posted id; `bot.add_dynamic_items` on a real client
  and a click after a real restart were not exercised.
- **No marathon has gone over under the bot.** The automatic trigger, the once-per-boot retry and "never twice" were
  driven by an injected clock and a fresh cog standing in for a boot.
- **The live events list was read twice from the build machine** (curl and `ScheduleClient.events()`, 2026-09-25
  13:1x, 70 events, next → 71). **Not from Fly** (KI-30's datacenter wall untested on this route).
- **The page was rendered once** against the mock on port 8794: the list (strip, Next up column), Halo Fest's drawer
  (Next up card, Re-read field) and one **Add it** click, which opened the new row and relinked Halo Fest — **no console
  errors**. Not Not this one, Look again, Mark it upcoming / live or Save from the browser; those were checked by
  `check.mjs` and the route tests.
- **Schema 61** was proven on a fresh file and a file downgraded to 60, not on the live volume.
- **Shadow** was tested against the fake shadow channel, not `#welcome-test`.
- **Discord's rendering** of `<t:…:D>`, a struck-through notice, and disabled buttons after an edit were not seen.
