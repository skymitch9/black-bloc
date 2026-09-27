# The marathon inbox — one master thread in events where detected marathons are managed, and a thread per marathon once it is tracked

> 🔨 **2026-09-26 — BUILT on branch `marathon-inbox` (off `main` `56056053`, schema 71, keys 543, routes 261), NOT merged, NOT deployed** — the numbered Deviations and *What was NOT verified* at the foot. ⚠️ **Live-behaviour change on deploy: an untracked marathon posts NOTHING** (board, reminders, shoutouts, next-event notice) — SS4C (live now, ends 2026-09-28) and Fall Fest (2026-10-08) go quiet until staff press **Track** (owner D1).

> **Audience:** the build agent (a cloud agent under an Opus 5.5 conductor, per the owner 2026-09-26 14:3x) and reviewers.
> **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-26 14:3x Phoenix), NOT built** — queued for the Sunday 2026-09-27 16:00 weekly reset, AFTER `marathon-archive` (`marathon-archive-design.md`) since it reads the archive. Branch `marathon-inbox`, off the archive branch or the `main` that holds it. Schema **71** if the archive took 70.
> **Last verified: 2026-09-26 14:3x** — by reading the code on `main` `76501919`: `black_bloc/cogs/content/marathon_feeds.py` (`add_candidate` `:410`, `send_added_notice` `:454`, `notice_published` `:471`, `post_notice` `:527` → `cog._send_staff`, `notice_view` `:1232`, the persistent `FeedButton` / `NoticeModePick` items, `claim_notice` and `marathons.noticed_at` from v171), `black_bloc/settings_store.py:4682` `marathon_notice_home` (*events* = a post in the events forum tagged marathon while events are reviewed in a forum, else the staff channel; *staff* = `staff_channel_id`; shadow rehearses in `shadow_channel_id`), `:4469` `marathon_channel_id` (the board, reminders and shoutouts; blank = the go-live channel), `black_bloc/cogs/content/marathon.py` (the board `board_channel_id` / `board_message_id` / `board_pinned` on the row, `refresh_marathon`, `tick_marathon`, `sync_window`, the reminders and shoutouts), `black_bloc/marathon_events.py` + `marathon-event-modes-design.md` (event modes none / marathon / runs / both), the thread precedents `cogs/moderation/modmail.py:1626` (`parent.create_thread`) and `cogs/community/requests.py:412` (`forum.create_thread`), `black_bloc/shadow.py` (the per-feature shadow home). ⚠️ NOT verified: nothing was run; no Discord surface was opened. Secret NAMES only.

## The ask, verbatim (owner, 2026-09-26 Phoenix)

- 13:4x: *"i think when a marathon is detected we should have a master point to manage them and then once managed they spawn a thread when accepted as a marathon we want to track"*.
- 13:4x, to the question of where: *"can we have a master thread in events"*.
- 14:2x: *"do the design doc for both then im gonna swap to opus 5.5 as leading model with cloud agents to do the build"*.

## A. What is wrong today, named

A feed-found marathon is pre-loaded quietly (v171), its staff notice posts ONCE when the schedule is out (an embed with Pause / Remove / Read it now / an event-mode select / Manage… / People…, into `marathon_notice_home`), and from then on its board, reminders and shoutouts go to `marathon_channel_id` beside every other marathon's. So: the notice is a one-shot that scrolls away; there is no one place that shows *what has been found and what we chose*; and every tracked marathon's posts share one channel. Three real marathons are on the list today (SS4C live, Fall Fest coming, RGL's N64 by hand if staff paste it) and six GDQ-shaped rows; the list will only grow.

## B. The shape — one inbox thread, one thread per tracked marathon

### B1. The inbox (the master thread)

- **Where:** a thread the bot makes ONCE in the events channel and remembers — key **`marathon_inbox_channel_id`** (channel, blank = `events_announce_channel_id`, the events home the rest of the bot uses), thread id in a new one-row table **`marathon_inbox (guild_id PRIMARY KEY, channel_id, thread_id, made_at)`** (not a settings key: it is state the bot wrote, and a setting must never carry something staff did not type). Name from key **`marathon_inbox_thread_name`** (text, default *Marathons — found and tracked*). Made on the first tick that needs it, `auto_archive_duration` the longest Discord allows, and **un-archived by the bot** whenever it posts (Discord archives idle threads; the reconcile re-opens it and re-reads `thread_id` after taking the lock — checklist 37). If the thread is gone (deleted by a person), log `marathon.inbox_lost` (IMPORTANT) and make a new one on the next tick.
- **One message per detected marathon**, posted when the marathon is added (by a feed or by staff) and **edited in place** as facts change: an embed — title = the marathon's name; fields **When** (the span, or *dates not published yet*), **Source** (the feed / the site, as a link), **Channel** (`twitch.tv/login` and whether it takes marathons), **Schedule** (*not out yet* / *N runs · M BaF* — the People line), **Event** (the event-mode word), **State** (*Found {when} · not tracked* / *Tracked by {who} {when}* / *Ignored by {who} {when}* / *Archived {when}*); message id in a new column **`marathons.inbox_message_id`**. The v171 notice folds into this message: **`send_added_notice` / `notice_published` post or edit the inbox message instead of a separate staff notice** (one fact, one home); `marathons.noticed_at` keeps meaning "the schedule-out moment was surfaced" and is set when the inbox message is edited to show runs. The old `marathon_notice_home` key is retired to `archive/` semantics: keep the key so old rows validate, mark its help *retired 2026-09 — the inbox thread is the notice home*, and stop reading it (checklist 35: the DECIDED bullet in `marathon-feeds-design.md` §D that made the notice gets a dated line).
- **Buttons on every inbox message** (persistent `DynamicItem`s, the `FeedButton` pattern with the marathon id in the custom id): **Track** · **Ignore** · **Open on the site ↗** (a link button to `events.html#marathon-<id>`); after Track: **Untrack** · **Open the thread ↗**; after Ignore: **Track anyway**. Staff role gated like every marathon move; a non-staff press gets the standing three-part refusal in words.
- The inbox message is the marathon's one Discord surface until it is tracked — the existing notice's Pause / Remove / Read it now / event-mode select / Manage… / People… stay reachable through `/event ▸ Marathons…` and the site, not on the inbox message (the inbox answers *what is this and do we want it*; the panel answers *manage it*).

### B2. Tracking — the marathon's own thread

- New columns **`marathons.tracked_at`**, **`tracked_by`**, **`thread_id`**, **`ignored_at`**, **`ignored_by`** (all nullable; schema +1). A marathon is **tracked** when `tracked_at` is set and `ignored_at` is not.
- **Track** (button, the drawer, the panel, `POST /api/marathons/{id}/track`): sets `tracked_at/by`, makes the marathon's thread in **`marathon_thread_channel_id`** (channel, blank = the inbox's channel) named by **`marathon_thread_name_template`** (text, default *{marathon}*; fields `{marathon} {channel} {when}`), posts the first message there (key **`marathon_thread_opening_template`**, default *{marathon} — tracked by {who}. The board, reminders and shoutouts for BaF runs post here. Schedule: {url}*), pins nothing yet, and edits the inbox message's State. Log `marathon.tracked` (IMPORTANT).
- **From then on every post about that marathon goes INSIDE its thread:** the board (`board_channel_id` = the thread id; the pin becomes the thread's pinned message), the reminders and shoutouts, the *schedule changed* notes, the next-event suggestion, and the Discord event's announce line if event mode makes one. **Untracked marathons post nothing** — they are read and kept current quietly (the v171 rule, widened): `tick_marathon` / `refresh_marathon` still fetch, match people, set the ping window and edit the inbox message, but every `_post` short-circuits unless tracked. ⚠️ This changes live behaviour: SS4C and Fall Fest are posting to the marathon channel today (in shadow); after this build they post nowhere until staff press Track. Say so in the deploy line and in the owner's report; existing marathons start **untracked** (a one-time backfill that pre-tracks marathons that already have a board would be the alternative — DECIDE with the owner; the doc's default is untracked, because the ask was "once managed").
- **Untrack**: keeps the thread (archived on Discord, not deleted), clears `tracked_at`, posts stop. **Ignore**: sets `ignored_at/by`, edits the inbox message (*Ignored…*, one button *Track anyway*), the marathon stays on the site list with an *ignored* badge, still read on the far cadence so its dates stay right, never posts, and the feed's ignore list is NOT touched (ignoring on the inbox is a choice about posting, not about the feed re-adding — the feed's Remove/ignore stays what it is). Staff final say every way round.
- **Archive** (`marathon-archive-design.md`): an archived marathon's thread is archived on Discord and its inbox message edited to *Archived {when}* with no buttons but **Open on the site ↗**.
- **`marathon_channel_id`** keeps one job: where the board goes for a marathon that is tracked but has no thread (the key **`marathon_track_makes_thread`**, bool, default **on**; off = Track without a thread, posts to `marathon_channel_id` as today — the owner's "spawn a thread" is the default, the old shape stays reachable, checklist 33).

### B3. Shadow, off, and the rehearsal

`marathon_mode = shadow`: the inbox thread and the marathon threads are made in the **shadow home** (`shadow.py`'s per-feature home for `marathon`, then the global `shadow_channel_id`), with the rehearsal note on the opening message; `on` makes them in the real channels; `off` makes nothing and edits nothing (the tick still fetches). The inbox thread id is stored per home, so flipping shadow → on makes a fresh real inbox rather than reusing the rehearsal one: table `marathon_inbox` gets a `home TEXT` column in its key (`guild_id, home`).

### B4. The site and the panel mirror it

- The Marathons table gets a **Tracked** column (*tracked · ignored · found*) and the drawer's header line 2 shows the state with the thread link (*thread ↗*). The moves bar gains **Track / Untrack / Ignore / Track anyway** (rendered only when valid, never a status menu). Settings foldout unchanged.
- `/event ▸ Marathons…`'s picked-marathon card gets the same moves (buttons, the `MarathonMove` pattern), and its header line says the state.
- `GET /api/marathons` rows carry `tracked_at, tracked_by, ignored_at, thread_id, thread_url, inbox_message_url`; the contract lists the two new routes (`/track`, `/ignore` with `{on: true|false}`). The mock mirrors all of it (one tracked marathon with a thread url, one ignored, one found).

### B5. Keys (checklist 33; every posted word)

`marathon_inbox_channel_id` (channel, blank = events announce channel) · `marathon_inbox_thread_name` · `marathon_thread_channel_id` · `marathon_thread_name_template` · `marathon_thread_opening_template` · `marathon_track_makes_thread` (bool, on) · the inbox embed's field labels (six text keys, the `NOTICE_*` labels in `marathon_feeds.py` today become keys — the standing every-word rule) · the State words (`marathon_inbox_state_found / tracked / ignored / archived` templates) · the button labels (`marathon_inbox_button_track / ignore / untrack / track_anyway / open_site / open_thread`) · the refusal for a marathon that cannot be tracked (no channel row / opted-out channel: *{marathon}'s channel is opted out of marathons — opt it back in on Go-live first*). Registry count moves accordingly; `architecture.md` updated.

## C. Tests, docs, gate

Tests mirror the package: `tests/cogs/content/test_marathon_feeds.py` (the added notice becomes an inbox message; the schedule-out edit sets `noticed_at`; a lost thread is remade), `tests/cogs/content/test_marathon.py` (an untracked marathon fetches, matches, sets its window and posts NOTHING; Track makes the thread and the board posts inside it; Untrack archives the thread; Ignore stops posts and keeps the row; shadow makes the threads in the shadow home; the reconcile re-reads the thread id under the lock), `tests/api/tools/test_marathons.py` (the two routes, the new row fields, the refusal), `tests/storage/test_db.py` (the schema step), node tests for the site words. Docs the build writes: this file's **Deviations** and **What was NOT verified**, `code-notes.md`, `architecture.md`, `sweeps.md` rows `MI-a…` (a: a feed-found marathon appears in the inbox thread with Track / Ignore and no other post; b: Track makes the thread and the board lands inside it; c: Ignore keeps it on the site and posts nothing; d: the schedule-out moment edits the inbox message; e: Untrack archives the thread), one dated line at the top of `marathon-feeds-design.md` (§D notice → inbox), `shadow-home-per-feature-design.md` (§E) and `marathon-schedule-design.md` (§D posts → the thread). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md` / the READMEs. Gate as `marathon-archive-design.md` §D, plus a headless render of the drawer with each of the three states.

Commit at clean boundaries in this order: schema + the inbox table → the inbox message replacing the notice → Track / the thread / posts inside it → Ignore / Untrack → the site + panel → docs. Finish fewer things completely rather than leave one half-built.

## D. Decisions still open (put to the owner one at a time before or during the build)

1. **Existing marathons:** start untracked (the doc's default), or pre-track the ones that already have a board (SS4C's, Fall Fest's)? ✅ **DECIDED 2026-09-26 16:4x (owner, verbatim): *"start untracked"*.** No backfill; every marathon on the list starts untracked and posts nothing until staff press Track.
2. **Where the marathon threads spawn:** the inbox's channel (events, the default here), or `marathon_channel_id` (the marathon channel) — the owner said *a master thread in events* for the inbox and did not say where the per-marathon threads go. ✅ **DECIDED 2026-09-26 16:4x (owner: *"a"*): the events channel**, beside the master thread — `marathon_thread_channel_id` blank = the inbox's channel stays the default.
3. **Track default for `action = add` feeds:** the inbox is the master point, so a feed's *add* no longer means *post*; should a key `marathon_track_default` (ask / track, default ask) exist so a trusted feed such as GDQ can auto-track? Default in this doc: no such key yet; Track is always a staff press. ✅ **DECIDED 2026-09-26 16:5x (owner, verbatim): *"a but lets build in a way to set autos"*** — Track stays a staff press by default, AND the build adds a per-feed **auto-track** switch: column `marathon_feeds.auto_track` (INTEGER NOT NULL DEFAULT 0), set from the feed drawer on the site, the feed card in `/event ▸ Marathons… ▸ Sources`, and `PATCH /api/marathons/feeds/{id}` (`auto_track`); when on, a marathon that feed adds is tracked automatically (thread made, `tracked_by` NULL, log `marathon.tracked` with `automatic: true`) the moment its schedule is out — the same moment the inbox message shows runs. All seven feeds start OFF. Plus a guild key `marathon_auto_track_default` (bool, default off) that a NEW feed copies at creation.

## E. Dispatch notes for the next conductor

See `marathon-archive-design.md` §E (cloud agents ran locally on 2026-09-26; build order archive → inbox; the merged `marathon-spotlight` schema 69 is not deployed yet). This build is the largest of the three (a feature across the feeds cog, the marathon cog, the API, the site, the mock): expect the 400–500k Opus range measured for multi-layer builds; commit and push on every boundary above so a kill loses nothing.

## Deviations

Written by the build (Opus 5.5, branch `marathon-inbox`, 2026-09-26). Where the spec and the code disagreed, the code's
pattern won for shape and the spec for behaviour.

1. ⚠️ **LIVE BEHAVIOUR CHANGE — every marathon starts untracked and posts nothing (owner D1, no backfill).** After the
   deploy SS4C (*Speed Stuff 4 LHS 2026*, running until 2026-09-28) and *Fastest Furs Fall Fest 2026* (2026-10-08) stop
   posting their board, reminders and shoutouts until staff press **Track** on their inbox message, the `/event` card or
   the drawer. A board already up from before is no longer edited; its pin still comes off a day after the end (the
   unpin is carried whatever the tracking says — checklist 38). Say it in the deploy line.
2. ~~**Every marathon's inbox message posts when it is added — feed or staff — and every marathon already on the list gets
   its message on the first tick after the deploy** (about nine messages into a new thread; in `shadow` that thread is in
   the shadow home). This retires `marathon_feed_notice_when` (v171's *published* = the notice waits for the schedule):
   the inbox message is there from the add, and the schedule-out moment is now an EDIT of it (`noticed_at` claimed first,
   `marathon.inbox_published`, then the feed's auto-track). The key stays so old rows validate; its help says *retired*.~~
   **REVERSED 2026-09-26 by `marathon-inbox-when`** — owner 17:5x, verbatim: *"i think we should only post when a
   schedule is live, keep that part"*. Why: a found marathon with no schedule is nothing staff can act on yet, and nine
   messages at once into a new thread buried the two that were real. Now `marathon_feed_notice_when` is live again:
   `published` (default) posts a marathon's inbox message — feed-made AND staff-made — on the first read that finds runs,
   `added` restores the post at add; the first tick after the deploy posts only marathons whose schedule has runs; staff
   can post one early with **Post it to the inbox now**. See *Follow-up — marathon-inbox-when* below.
   The DECIDED bullet in `marathon-feeds-design.md` carries the dated line (checklist 35). The line above a feed-found
   marathon's message is still `marathon_feed_added_template`.
3. **`marathon_notice_home` and `marathon_notice_title_template` are retired** (help says so, nothing reads them): every
   staff notice — a suggest-mode feed's *Add it / Not this one*, a GDQ marathon's next-event suggestion — goes into the
   inbox thread; a next-event notice of a TRACKED marathon that has a thread goes into that thread instead. An untracked
   marathon's next-event notice still posts (in the inbox): it is about a new marathon, not about this one's posts.
   `events.open_notice_post` has no caller any more and was left in place.
4. **Two columns the design did not name: `marathons.inbox_home` and `marathons.thread_home`** (`on` / `shadow`), beside
   the design's `(guild_id, home)` key on `marathon_inbox`. A mode flip then makes a FRESH real inbox message and a fresh
   real thread (`marathon.thread_made` carries `replaced`) instead of editing the rehearsal copies.
5. **The inbox's channel is `marathon_inbox_channel_id`, blank = `events_announce_channel_id`**, whose registry default is
   the live-now channel when unset. A forum parent is supported (the inbox is then one post whose first message is the
   opening line); a text channel gets a public thread and the opening as its first message. A new key
   `marathon_inbox_opening` carries that line (every-word rule).
6. **Thirty-five keys, not the design's list.** The design's eight + six labels + three State words + six buttons + the
   refusal, plus: `marathon_auto_track_default` (D3), `marathon_inbox_opening`, `marathon_inbox_auto_who` (*the {feed}
   feed*), five value words (`_no_dates`, `_schedule_none`, `_schedule_runs`, `_no_channel`, `_channel_opted_out`),
   `marathon_not_tracked` (the refusal when staff ask an untracked marathon to post), and four answers
   (`marathon_tracked_said`, `_untracked_said`, `_ignored_said`, `_unignored_said`). The *Archived* State word is
   `marathon_archived_word` — one fact, one home — not a fourth State key. Panel button labels stay code constants like
   every other panel move.
7. **`POST /ignore {on: false}` puts an ignored marathon back to *found*** (`marathon.unignored`) — the reverse the
   design's `{on: true|false}` implied; *Track anyway* is Track. `POST /track {on: false}` is Untrack.
8. **Track refuses only an opted-out channel** (`marathon_track_refused`, 409 `channel_opted_out`). A marathon with no
   channel row at all can be tracked — it posted before this build, and its board links the schedule instead.
9. **Staff moves that post are refused in words on an untracked marathon** — *Post the board* and *Shout it now* answer
   409 `not_tracked` (`marathon_not_tracked`), and the site does not draw them until it is tracked. *Mark it live* still
   moves the run and shouts only when tracked.
10. **Untrack unpins the board and archives the thread** (kept, not deleted; Track again re-opens the SAME thread).
    Ignoring a tracked marathon does both too. Ignore never touches the feed's ignore list.
11. **Not moved into the thread, because they are not the marathon's posts:** there is no separate *schedule changed*
    post (it is a log row), and the Discord event's announce line belongs to the events feature.
12. **The inbox message is edited only when what it shows changes**, compared in memory, and re-read at most every
    `RECHECK_MINUTES` (60) — so a person deleting the inbox thread is noticed within the hour (`marathon.inbox_lost`
    IMPORTANT, then a new thread), not within the minute, without a fetch per marathon per tick.
13. **An ignored marathon is read on the far cadence only** (`marathon_far_poll_hours` since the last read), so its dates
    stay right; its run states still move, and nothing posts.
14. **Auto-track** runs inside the schedule-out moment, after `noticed_at` is claimed, so it fires once; `tracked_by` NULL,
    `marathon.tracked` with `automatic: true` and the `feed_id` (the log's `via` word normalises `feed` to Discord, as
    every feed row already does). A seeded feed copies `marathon_auto_track_default` like a staff-made one. An Untrack
    after an auto-track sticks.
15. **The tracked answer says where in words** (*its own thread, beside the inbox* / *the marathon channel*), not a `<#id>`
    mention, because the same sentence is shown on the site.
16. **Off** tracks the row but makes and edits nothing; the thread is made at the first post once the mode is `shadow` or
    `on`.
17. **The v171–v175 added-notice buttons (Pause it / Remove it / Read it now / the Event select / Manage…) stay
    registered** so notices already posted keep answering; nothing posts new ones. Their tests now build such a notice.
18. **One commit for §C's middle boundaries** (the inbox message, Track and the thread, Ignore / Untrack): they share the
    same functions in `marathon.py`, `marathon_feeds.py` and the new `marathon_inbox.py`, and splitting them would have
    left a half-built middle. Schema, site and docs are their own commits.
19. **The mock** has no tick and no threads: Track gives a fake thread id, the inbox message link points at a fake inbox
    thread; AGDQ 2027 is seeded tracked, Flame Fatales ignored, the rest found.

## What was NOT verified

- **Nothing met Discord.** The bot was not run. Thread creation, the forum-parent path, un-archiving, `guild.fetch_channel`
  for archived threads, the persistent Inbox buttons in a real client and the link buttons were exercised against test
  fakes only. Discord's own limits (thread-name length is clamped to 100; `auto_archive_duration` 10080 needs no boost
  today) were not re-checked against the API.
- **The live database was not read and schema 71 has NOT run on it** — proved on a fresh file and a downgraded 70 file in
  tests only. The live `events_announce_channel_id` value (the inbox's home) was not looked up.
- **The first-tick burst** (one inbox message per marathon already on the list) was reasoned about and covered by the
  tick tests, not watched.
- **Rendered** in `chrome-headless-shell` 149.0.7827.22 over raw CDP against this branch's mock (`MOCK_PORT=8812`): the
  Marathons table with the Tracked column (1400 px), the drawer tracked (AGDQ 2027, 1400 and 390 px — no horizontal
  scroll), ignored (Flame Fatales 2026) and found (GDQx 2026, then **Track** clicked — the drawer re-rendered tracked),
  and the GDQ feed drawer with the Auto-track switch (switched On, the answer shown); zero console errors. NOT rendered:
  the light theme, the `/event` panel card (tests only), an archived drawer's new fields.

