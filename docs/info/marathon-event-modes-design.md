# A marathon's event mode — none, the marathon, our runs, or both; and the staff notice lives in Events

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-25 14:5x Phoenix)
> — dispatches to Opus as branch `marathon-event-modes` AFTER `marathon-feeds` merges** (both touch `create_marathon`,
> the Add form and the staff notice). **Last verified: 2026-09-25 14:4x** — live settings through the operator token:
> `events_review_mode = forum`, `events_forum_channel_id` set (the Events forum under BlackMail),
> `events_announce_channel_id` set (*where an approved event is announced and pinged when it starts*),
> `staff_channel_id` = `#the-main-table`, `marathon_mode = shadow`. Code (v164): `cogs/content/marathon.py` —
> `make_event_for` / `make_event_now` / `event_follows` / `redate_event` (the marathon-level event, made through
> `cogs/community/events.py:propose_from`, re-dated through `events.move_scheduled_event`), the staff notice
> `_notice` (~:1415–1435, posts to `staff_channel_id`, rehearses in the shadow home), `marathons.event_id` +
> `event_wanted` (schema 62), `marathon_makes_event` (bool, true), the Add form's *Also make it an event* box and the
> `/event` ▸ Marathons… Add modal's fifth field; `cogs/community/events.py:open_forum_post` (~:391) — one forum post
> per event in forum mode, `forum_tags` / `tags_for_status`; `marathon_runs` (`state`, `people`, `scheduled_at`,
> `ends_at`, `shout_message_id`). ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-25 14:4x Phoenix)

*"post it in events but dont make an event by default for a marathon, add a few options, 1 being make an event, 2
being make an event just for BaF runner (then update this event with the schedule api so it stays current), 3 skip
event tracking. does that cover all use cases?"*

**Read as:** (a) the marathon staff notice belongs with the events, not in the staff channel; (b) the shipped default
(*Also make it an event*, on) is wrong — the default is **no event**; (c) three modes, per marathon, with a fourth
that costs nothing: **none** · **marathon** (one event for the whole marathon, as shipped) · **runs** (one event per
run of OURS, dated from the schedule and re-dated as it moves) · **both**. The answer to *"does that cover all use
cases?"*: yes, plus *both*, plus one collision to settle — an event of its own means the EVENTS feature announces
that run when it starts, in `events_announce_channel_id` with its ping, and the marathon shoutout would then say the
same thing a second time. §C settles it with a key.

## A. The model — one mode word per marathon, and an event per run in `runs` mode

- **`marathons.event_mode TEXT NOT NULL DEFAULT 'none'`** (`ADDED_COLUMNS`, schema 63 → **64** if `marathon-feeds`
  took 63): `none` / `marathon` / `runs` / `both`. `event_wanted` is retired (its meaning — "wanted, schedule not
  published yet" — becomes `event_mode in (marathon, both) AND event_id IS NULL`); its column stays, unread, additive
  only. **`marathon_feeds.event_mode`** (same words, the mode a feed-made marathon gets) — the feeds build's default
  `marathon_makes_event` becomes this. **Owner, 2026-09-25 14:5x, verbatim: *"lets opt esam out of events"*** — the ESA
  feed (the `horaro` feed on the `esamarathon` row) is seeded with `event_mode = none` EXPLICITLY, and stays `none`
  whatever `marathon_event_mode_default` says, until staff change it on the feed's row; every marathon it makes
  inherits that. ESA still gets its board, reminders and shoutouts for our runners — only the Events rows are off. `marathon_makes_event` (bool) is retired in favour of
  **`marathon_event_mode_default`** (enum, **`none`**).
- **`marathon_runs.event_id INTEGER`** (nullable): the run's own event in `runs` / `both` mode. Made when a run IS ours
  (on the first fetch that matches a person, on a pairing that makes it ours, and on a mode change to `runs`/`both`
  for every run of ours already there), title from `marathon_run_event_title_template` (*{member} runs {game} at
  {marathon}* — several members → the names joined), description from `marathon_run_event_description_template`
  (*{category} · {marathon} · read from the schedule; times follow it.*), Where = the marathon channel's URL (else the
  runner's), starts = `scheduled_at`, ends = `ends_at`. Re-dated on every fetch that moves the run (through
  `events.move_scheduled_event`, `marathon.run_event_redated`); **cancelled** with reason `run_dropped` when the run is
  dropped, `not_ours` when a pairing is removed and nobody of ours is left, `marathon_removed` with the marathon, and
  `mode_changed` when staff leave `runs`/`both` (`marathon_run_event_cancel_on_leave`, bool, true — off keeps them).
- **Review or not.** The marathon-level event keeps going through the events review (the raid-train precedent, as
  shipped). A RUN event is made **approved directly** when `marathon_run_events_reviewed` (bool, **false**) — staff
  chose the mode, and a review post per run of ours would be a queue nobody asked for; the key turns the review back
  on. Staff final say is the event's own Cancel, and the marathon drawer's **Unlink** / **Make it now** per run.

## B. The doors

- The Add form's *Also make it an event* box becomes an **Event** select — *No event* / *One event for the marathon*
  / *An event per run of ours* / *Both* — default from `marathon_event_mode_default`; the same select on the marathon
  drawer's Event card (changing it applies at once: makes, or cancels per §A) and on a feed's row (the mode its
  marathons get). The `/event` ▸ Marathons… Add modal's fifth field becomes *Event: none / marathon / runs / both*; the
  marathon card gains **Event mode…** (a select) and each run of ours in the run view shows *event #N* with **Unlink**
  / **Make it now**. Routes: `PATCH /api/marathons/{id}` accepts `event_mode`; `POST /api/marathons` takes
  `event_mode` (the old `make_event` still accepted, mapped to `marathon` for one release, then gone); `POST` /
  `DELETE …/runs/{run_id}/event`. The Events page's queue rows made this way carry a *marathon run* badge beside the
  existing *marathon* one; the event detail card links the run.

## C. The two posts that would say the same thing

A run with its own event is announced by the EVENTS feature when it starts (the existing *ping when an event goes
live* in `events_announce_channel_id`). So: **`marathon_shout_when_run_has_event`** (bool, **false**) — when a run of
ours has an event, the marathon **shoutout** for that run is skipped (`marathon.shout_skipped`, `because: run_event`)
and the events announcement is the shoutout; the 15-minute marathon **reminder** still posts (events have no
reminder of their own), pinging as today. On, both post. The board is unchanged.

## D. The staff notice lives in Events

**`marathon_notice_home`** (enum `events` / `staff`, **`events`**). `events`: in forum mode the notice is a **post in
`events_forum_channel_id`** through `open_forum_post` (title *New marathon: {name}*, tag *marathon* — added to the
forum's tags the way status tags are), the buttons on the post's first message; in room mode it is a message in the
staff channel (there is no room without a proposal). `staff`: today's behaviour. Shadow unchanged (the shadow home
with the note). The notice's outcome edits stay as built. This covers every marathon notice: the next-event
suggestion, the feed's *added* notice, and the feed's suggestion.

## E. Keys — seven new, two retired

`marathon_event_mode_default` (enum, `none`), `marathon_run_event_title_template`, `marathon_run_event_description_template`,
`marathon_run_events_reviewed` (bool, false), `marathon_run_event_cancel_on_leave` (bool, true),
`marathon_shout_when_run_has_event` (bool, false), `marathon_notice_home` (enum, `events`); retired: `marathon_makes_event`
(the registry drops it; a stored value is ignored — say so in code-notes). Registry + mock + labels + the Marathons group.

## F. Logging

`marathon.run_event_made / run_event_redated / run_event_cancelled / run_event_failed` (failed IMPORTANT by suffix),
`marathon.event_mode_set` (`from`, `to`, `via`), `marathon.shout_skipped`, `marathon.notice_posted` gains `home`.

## G. Tests, docs, gate

`tests/cogs/content/test_marathon.py` (default `none` makes nothing; `marathon` as shipped; `runs`: an event per run
of ours, made on match / pairing / mode change, approved directly unless the key, re-dated on a move, cancelled on
drop / unpair / remove / mode leave and kept when the leave key is off; `both`; the shoutout is skipped when the run
has an event and posts when the key is on; the notice lands in the forum in forum mode, the staff channel in room
mode, the shadow home in shadow), `tests/cogs/community/test_events.py` (the forum post + tag; the *marathon run*
badge data), `tests/api/tools/test_marathons.py` (`event_mode` on POST/PATCH, the run event routes, `make_event`
mapped), `tests/api/tools/test_events.py`, contract, `test_db.py`, the key / kind guards, `check.mjs`. Both `pytest
-n 8` orders, `ruff`, ES parse, node tests, a mock port of the builder's own. Docs: `code-notes.md`; this doc's foot;
`architecture.md`; `docs/info/README.md` (one row); `marathon-events-page-design.md` and `marathon-feeds-design.md`
one dated line each (the default flipped to none; the notice moved); `sweeps.md` rows `MV-a…` (a: Add a marathon
shows *No event* selected; b: *An event per run of ours* on AGDQ 2027 makes one approved event per run of ours in the
queue; c: a moved run re-dates its event; d: the new-marathon notice is a post in the Events forum). NOT `TODO.md` /
`DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`. ⚠️ Migrate before deploy: two columns through `ADDED_COLUMNS`.

## Deviations

*(the build agent writes this)*

## What was NOT verified

*(the build agent writes this)*
