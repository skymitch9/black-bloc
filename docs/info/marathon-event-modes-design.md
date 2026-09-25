# A marathon's event mode — none, the marathon, our runs, or both; and the staff notice lives in Events

> 🔨 **2026-09-25 — the page and panel shapes moved, branch `marathon-ux` (NOT merged):** the marathon drawer now opens on a **Schedule** card (source, last read, next read, the Re-read-every field, Read it now), then Runs · Who is who · Event · The channel · Posts · Pause/Remove; the Events page is three sections; feeds sit in a *Where marathons come from* foldout whose rows open a feed drawer; *ours* reads **BaF**. Where this doc describes the old page or panel layout, [`marathon-ux-design.md`](marathon-ux-design.md) wins.

> ✅ **2026-09-25 16:15 — LIVE as v165** (release commit `2351311a`, merge `ba513bb9`). Boot log: `database: added marathons.event_mode` / `marathons.held_by_channel` / `marathon_runs.event_id` / `marathon_feeds.event_mode` / `marathon_feeds.held_by_channel` / `spotlight_channels.marathons` at 23:15:04Z (schema 64); first boot `golive.channel_marathons_set esamarathon from=True to=False` 23:15:07Z, no event wish made. ⚠️ Nothing has met Discord by hand; no run event approved against Discord; the notice not seen in forum mode (live is shadow); sweeps `MV-a`…`MV-f` are the owner's.

> 🔨 **2026-09-25 — BUILT on branch `marathon-event-modes` (off `main` `bababb65`), NOT merged, NOT deployed.** Schema 64, keys 475 → 482, 16 deviations (⚠️ 3: run events are reviewed while `marathon_mode` is shadow; ⚠️ 6: `event_id = 0` marks a run staff unlinked; ⚠️ 11: the knock-on rows are bare) and *What was NOT verified* at the foot.

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

## A2. A channel row can opt OUT of marathons altogether

**Owner, 2026-09-25 15:0x, verbatim: *"yes have esam opted out for marathons, make sure any channel only can opt out of
marathons"*.** `spotlight_channels.marathons INTEGER NOT NULL DEFAULT 1` (`ADDED_COLUMNS`, the same schema bump), a
toggle beside `announce` and `spotlight`. Off means: no feed is seeded for the row and an existing feed on it is
paused (`marathon.feed_paused`, `because: channel_opted_out`) and cannot be resumed while it is off; **Add a
marathon** refuses that channel row in words (*ESAMarathon is opted out of marathons — turn it on in its row
first.*); marathons already on it are paused the same way and resume when it goes back on. **The ESA row
(`esamarathon`) is seeded OFF** by the same boot reconcile that seeds feeds; every other row is on. Doors: the
Go-live page row drawer's Announcements card gains **Marathons: on / off** (a segment, staff), the row's Announced
cell reads `· no marathons` when off; `/golive` ▸ Channels… gains **Marathons on** / **Marathons off** on the picked
channel; `PATCH /api/golive/spotlight/{id}` accepts `marathons`; the row carries `marathons` and the join fixture
gains it. Log `golive.channel_marathons_set` (`from`, `to`, `via`, routine). This supersedes the ESA
`event_mode = none` note in §A — ESA gets no marathons at all, so no events either.

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

*(written by the build agent, 2026-09-25, branch `marathon-event-modes` off `main` `bababb65`. Schema **63 → 64**,
registry keys **475 → 482**, real routes **+2** (the contract carries **+4** entries — `check.mjs` reads *22 pages, 250
routes*), log kinds **+10**. Cogs, pages and top-level commands unchanged.)*

1. **Schema 64, six columns, not two** (`ADDED_COLUMNS`): `marathons.event_mode`, `marathons.held_by_channel`,
   `marathon_runs.event_id`, `marathon_feeds.event_mode` (NULL = follow `marathon_event_mode_default`),
   `marathon_feeds.held_by_channel`, `spotlight_channels.marathons`. A **one-time backfill** runs only in the boot that
   adds `marathons.event_mode`: a marathon that had an event or the old wish becomes `marathon`, everything else `none`
   — so v164's live AGDQ-style rows keep their events and the NEW default is none.
2. **`held_by_channel` (not in §A2).** "Resume when it goes back on" needs to know WHICH marathons the opt-out paused —
   a pause staff made before must stay (staff final say). Held rows (marathons and the feed) are marked and only they
   come back. A held marathon's **Resume** is refused in words while the channel is off, like the feed's (§A2 named
   only the feed).
3. ⚠️ **Run events skip the review only while `marathon_mode` is `on`.** In `shadow` (the live setting) a run event
   goes through the events review like the marathon-level one, as if `marathon_run_events_reviewed` were on: an approved
   run event is a Discord scheduled event plus a ping in `events_announce_channel_id` at its start, and the review
   checklist's rule is that anything a build makes that POSTS ships shadow. `marathon.run_event_made` carries
   `reviewed`.
4. **The ESA opt-out is seeded once, ever**, beside the feed seeds, in `marathon_feed_seeds` under the key
   `optout:esamarathon` — a staff turn-back-on is never undone by the next boot. The feed seed skips an opted-out
   channel WITHOUT marking it, so a channel turned back on is offered its seed on the next boot. Add a feed and Move to
   channel never offer an opted-out row (the route refuses one in words too).
5. **Moving a marathon onto an opted-out channel is refused** (`set_channel`), as is Add a marathon (§A2 named Add).
6. ⚠️ **`marathon_runs.event_id = 0` means "staff unlinked"** — Unlink must stick, and in `runs` mode the next read
   would otherwise make the event again. **Make it now** works in any mode and clears it. A LINKED run is kept in step
   (re-dated, or called off when dropped / no longer ours) whatever the mode; only MAKING is gated by the mode (and by
   the marathon being active and the run not yet over).
7. **Eight keys, not seven: `marathon_notice_title_template`** (*New marathon: {name}*) — the forum post's name is a
   posted word, so it is a key. ⚠️ **The forum tag's name, `marathon`, is a constant**, not a key: a renamed key would
   mint a second tag on the forum. Flagged against the every-word rule for the conductor. The tag is added to an
   existing forum the first time a notice asks for it (`events.forum_tag`), NOT at **Make the forum** — that forum's
   made tags stay the six statuses the events tests pin; a full forum (20 tags) posts untagged.
8. **`marathon.notice_posted` did not exist; it is new** (one row per notice that goes up, `home` = events / staff /
   shadow, plus what the notice is about). A forum that refuses the post falls back to the staff channel with
   `marathon.notice_forum_failed` (IMPORTANT by suffix). A next-event record now carries `notice_home` so its fold
   knows a forum post is not a rehearsal; old records fall back to the old channel comparison.
9. **Log kinds beyond §F:** `run_event_unlinked` (the staff door), `notice_forum_failed`, `golive.channel_marathons_set`
   (§A2). Leaving `runs` with the cancel key OFF writes no per-run row; `marathon.event_mode_set` carries `kept` /
   `cancelled` / `made` counts. The 10: routine `event_mode_set`, `notice_posted`, `run_event_made`,
   `run_event_redated`, `run_event_cancelled`, `run_event_unlinked`, `shout_skipped`, `golive.channel_marathons_set`;
   suffix `run_event_failed`, `notice_forum_failed`.
10. **Make an event now / Unlink move the mode's marathon half** (`none`→`marathon`, `runs`→`both` and back), so the
    mode never lies about what the marathon keeps. A wish that cannot be met (nobody to propose as, the review refused)
    drops the marathon half (`stop_waiting`) — exactly what `event_wanted = 0` did, so a read does not retry it forever.
11. ⚠️ **The knock-on rows are bare** (checklist 34): run events made or called off by an Add, a mode PATCH, a pairing or
    a read carry no `web.` head; the marathon event a mode change makes or calls off is bare too. Add's own marathon
    event keeps its shipped `web.marathon.event_made` (the existing test pins it). To keep that, `create_marathon`
    inserts with mode `none` and writes the chosen mode after the first read.
12. **Discord doors:** the Add modal's fifth field takes a mode word (yes / no still map for one release); the card's
    **Event mode…** is a select (row 1); a run's **Unlink** / **Make it now** sit on row 3; the Feeds card gains an
    event select (with *Whatever the setting says*), **Rename…** (a modal) and **Move to channel…** (a channel-select
    view, only rows without a feed that take marathons). `/golive` ▸ **Channels…** gains **Marathons on / off** and a
    *Marathons:* line for the picked row.
13. **Site doors:** the Add form's **Event** select, the drawer's Event card select (applies at once, reverts on a
    refusal), each run's *event #N* link + **Unlink** / **Make it now** and an *event #N* badge, the Feeds card's
    **Event** column + **Rename…** / **Move to channel…**, the queue's *marathon run* badge (beside *marathon*) and the
    detail card's **Marathon run** line. The Go-live drawer's segment is IN the Announcements card (as §A2 says); the
    Add form's channel picker greys out opted-out rows.
14. **Shout it now always posts** (staff final say); **Mark it live** by staff does not force — a run with an approved
    event is still announced by the events feature.
15. **Tests mirror the package** (the repo rule wins over §G's file names): `tests/cogs/content/test_marathon_events.py`,
    `tests/cogs/content/test_marathon_channels.py`, `tests/test_marathon_events.py`, `tests/test_marathon_channels.py`;
    `approved_from` and `forum_tag` in `tests/test_events.py`; the run link on `/api/events` in
    `tests/api/tools/test_marathons.py`. **Mock:** AGDQ 2027 is seeded in `both` with events on runs 5 and 7; the ESA
    row is `marathons: false`, so `check.mjs`'s `feedless_spotlight_id` moved to Frost Fatales (3).
16. **Sweep rows `MV-a` … `MV-f`** (`e` the channel opt-out, `f` the feed's doors). Commits carry the trailer of the model
    that did the work (Opus 5.5), not the brief's Fable 5.1 line.

## What was NOT verified

- ⚠️ **Nothing met Discord.** The forum-post notice (and adding the `marathon` tag to a real forum — `forum.edit`
  permissions), the Event mode select, the run view's Unlink / Make it now, the feed's Rename modal and Move view, and
  `/golive` ▸ Channels… Marathons on/off ran only against the suite's fakes.
- ⚠️ **No run event has been approved against Discord.** Every test turns `events_create_scheduled` off, so
  `approved_from`'s scheduled-event creation and the run-event re-date's `move_scheduled_event` were never exercised;
  nor was the events feature announcing a run event at its start — §C's "the events announcement is the shoutout" rests
  on the existing events sweep, not on a run here.
- ⚠️ **First boot after deploy:** the ESA row (live id 4) is opted out once — any marathon on it is paused (held) and its
  feed, if staff made one, paused. Every marathon that has an event today becomes `marathon` by the backfill; everything
  else, and every feed-made marathon from then on, makes NO event (the feeds build's "waiting event wish on each" no
  longer happens). With `marathon_mode = shadow` live, `runs` mode proposes run events through the review.
- **Schema 64** was proven on a fresh file and on a file with the six columns dropped and set back to 63 (the backfill,
  and that it does not run a second time), not on the live volume.
- **Shadow → reviewed** was tested with `propose_from` faked, as the shipped marathon-event tests do.
- **The page was rendered headless only** (Chrome `--dump-dom`, my mock on port 8798): AGDQ 2027's drawer shows
  *event #6 · live*, *event #7 · approved*, **Unlink** ×2 and **Make it now**, the Event select on *Both*; the Feeds
  card's Event select and Rename… / Move to channel…; the Go-live list's ESA cell *spotlight · … · no marathons*.
  **Nothing was clicked** and console errors were not read; the writes were checked by `check.mjs` and the route tests.
  The conductor's mock on 8797 still serves `main` until it is restarted after the merge.
- **Cost:** one extra `get_event` per linked run per read, and one event row per run of ours in `runs` mode. Not
  measured.
