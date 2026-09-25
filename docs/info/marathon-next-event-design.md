# The next GDQ event — suggested when a marathon ends, added by staff, never by itself

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

*(the build agent writes this)*

## What was NOT verified

*(the build agent writes this)*
