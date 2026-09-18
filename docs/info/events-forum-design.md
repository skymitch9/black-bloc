# Events as a forum under BlackMail — one post per event, like requests and modmail

> **Audience:** the build agent and reviewers. **Status:** TRACKED · ✅ **LIVE as v136** — merge `32f4827`, release `bb94a92`,
> deployed **2026-09-17 22:07** Phoenix, `events_review_mode` ships **room**; sweeps **596–602** are the owner's; verified: boot log clean (logged in 22:07:41, no traceback — the schema-45 column applied silently as ADDED_COLUMNS does), /health ready; Make the forum pressed on the events page 22:08 → POST /api/events/forum 200 and the guild lists forum #events 1550372982566686802 under BlackMail with the six tags (pending, approved, denied, live, done, cancelled) read by token; the reply names test mode and the claim. NOT yet: a post — that needs a proposed event after the mode flip (rows 597–602). Was: BUILT on branch `events-forum` off `main` `a7399b0`. Read the `## Deviations`
> foot BEFORE the sections above: **fifteen** things differ from what is written here, and deviations **1, 3, 5 and
> 6** are the ones that matter (six tags not five; an archived post is NOT a gone post; the retention sweep logs
> `event.post_archived` rather than claiming a deletion; there is no test-channel fall-back). Schema **44 → 45**
> (`events.review_kind`) — ⚠️ **migrate before deploy.** Registry **280 → 282**; `pytest -n 8` **6696 → 6755**, green
> forward and under `BB_REVERSE=1`; mock **20 pages / 187 routes**. `events_review_mode` ships **room**, so nothing
> changes until the owner flips it. Was: 📐 DESIGN, dispatched to Opus 2026-09-17 21:22. **Last verified: 2026-09-17 21:2x** against `main` `0707768` (v135): `black_bloc/events.py`
> `make_review_channel` (~1785, `guild.create_text_channel` under `events_category_id` or the test category, `staff_reach`
> overwrites, then `guard.own_channel`), `set_review` (~975: `review_channel_id`, `review_message_id`, `card_channel_id`),
> `card_channel` (~1040), every `guild.get_channel(row["review_channel_id"])` site (~1156, ~1370, cog ~452, ~1708–1711,
> ~1948–2043), the cog's `DecisionButton` (`event:<id>:approve|deny|delete_room|make_request`), the rooms rules in
> [`events-rooms-design.md`](events-rooms-design.md) (own the room, the event's posts land in it, **Delete this room**
> settles, test rooms go 5 minutes after the end, live rooms keep `events_channel_retention_days`); the forum pattern in
> [`blackmail-threads-design.md`](blackmail-threads-design.md) §A–§B + §F–§G and `cogs/community/requests.py`
> (`make_forum` ~922, `open_forum_post` ~391, `thread_of` ~363, `forum_tags`, `tags_for_status`, `forum_of` claims the
> forum for the guard on every read — v120). ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-17 21:2x)

*"can we have events also go down into the Black Mail section, and make a thread channel like we have for request and
modmail"*

**Reading.** Today every proposed event gets its own TEXT CHANNEL (the review room) under `events_category_id`. The
owner wants the same shape requests (v119 §B) and modmail (§A) have: ONE Discord **forum** channel under the BlackMail
category, and every event is a **post** in it — the review card and its decision buttons are the post's first message,
staff discuss in the post, the list never grows past the forum's own archive.

## A. Keys (every decision configurable both ways — registry + mock row + label; the `events` group already carries a
Find… box, so two more keys are fine there)

| Key | Kind | Default | Help |
|---|---|---|---|
| `events_review_mode` | enum `room` / `forum` | **`room`** (today, unchanged until the owner flips it) | *"room makes a text channel per event under events_category_id; forum makes one post per event in events_forum_channel_id (Make the forum on /event first)"* |
| `events_forum_channel_id` | channel | blank | *"the forum channel every event is posted in, in forum mode; Make the forum on /event's staff panel makes one under the BlackMail category"* |

Tags on the forum, made by **Make the forum** and looked up BY NAME each time (never an id in a key — the modmail /
requests rule): named exactly after `events.py`'s status constants — `pending` 🟡, `approved` 🟢, `denied` 🔴, `done` ✅,
`cancelled` ⚫ (and any other status the row can hold — `events.py:79–84` is the list; match it one for one and say so).

## B. Make the forum

`/event`'s STAFF panel (the settings / Where panel that already carries `events_category_id`) and the site's events
page gain **Make the forum**: `#events` as a forum under `modmail_category_id` (BlackMail — the same key requests use),
the category's overwrites + the bot's own allow (view, send, manage channels, manage threads, send in threads), the
five tags, `default_auto_archive_duration` = the requests value; writes `events_forum_channel_id`; refuses in words
when the key already points at a live forum, when there is no BlackMail category, or when the API is missing — copy
`requests.make_forum` line for line where it fits, and share a helper if one falls out cleanly (say so). Under
`TEST_MODE` the forum is made outside the test category (creation is not gated) and claimed with `guard.own_channel`
so the bot may post there; the reply says so. `forum_of` for events CLAIMS the forum on every read (the v120 lesson:
`owned_channel_ids` is in-memory and forgets on restart).

## C. Forum mode, event by event

- **Propose** → in forum mode `make_review_channel` is replaced by `open_review_post`: `forum.create_thread(name=<the
  event's title · its date in the guild's usual short form>, content=<the same first line the room gets>, embed=<the
  review card>, view=<the DecisionButtons>, applied_tags=[pending], auto_archive_duration=…, allowed_mentions none,
  reason=…)`. The THREAD id is stored where the room id goes (`review_channel_id`), the starter message id in
  `review_message_id`, and ⚠️ **`events.review_kind TEXT` ('room' / 'post', nullable — old rows read as room)** is
  added — schema 44 → **45** through `ADDED_COLUMNS` — so no site ever has to guess what kind of id it holds.
- **One resolver, `review_place(bot, guild, row)`**, replaces every bare `guild.get_channel(row["review_channel_id"])`:
  a room → `get_channel`; a post → `guild.get_thread(id)` then `bot.get_channel(id)` then a `fetch_channel` (the
  requests `thread_of` pattern). Every site listed in the header goes through it — including the decision gate
  (`interaction.channel_id` equals the thread id inside a post, so the gate still holds), the cancel-on-gone sweep
  (a deleted post is `review_channel_deleted`, an archived post is NOT gone), and the retention sweep.
- **Everything that lands in the room lands in the post** (the rooms design's Part 1: the event's own messages, the
  moves, the **Delete this room** card — retitled *Delete this post* in forum mode, same custom id, same settle rule).
  ⚠️ **The host is NOT added to the post.** BlackMail is staff-side; requests and modmail posts are staff-side; the host
  hears by DM exactly as a request's filer does (`events.py` already DMs every decision). Name this in Deviations if
  anything in the room path gave the host an overwrite — that line is skipped in forum mode.
- **Decisions edit the tag**: approve → `approved`, deny → `denied`, cancel → `cancelled`, the event's end → `done`;
  denied / cancelled / done posts are **archived**, never deleted by retention (`events_channel_retention_days` is a
  ROOM rule; in forum mode the sweep archives + tags instead and writes the same log kind with `kind: post`). Under
  `TEST_MODE` the 5-minutes-after-the-end deletion applies to posts too (a test post is deleted like a test room).
  **Delete this post** deletes the thread and settles exactly as the room button does.
- **Send to…** (`send-to-design.md`): request → event and ticket → event go through the same propose path, so they
  land in the forum with nothing extra; event → request already leaves the event settled — its post is tagged +
  archived. Say what was checked.
- **Mode flips**: `room` → `forum` affects NEW events only; open rooms stay rooms until they settle (`review_kind`
  says which is which — no migration of open rooms). `forum` → `room` the same in reverse. A forum mode with a blank
  or dead `events_forum_channel_id` refuses Propose in words naming **Make the forum** (staff) / *"staff have not set
  up the events forum yet"* (a member) — never a bare failure, never a silent fall-back to a room (a fall-back is how
  two modes survive).
- **Hand-made posts in the events forum** (the §G analogue for requests) are ⚠️ **NOT in this build** — the bot
  ignores threads it did not make (idempotent, checked by row like §G); name it in Deviations as deliberately absent.
- **Guard**: the forum is owned; in `TEST_MODE` the post is made only when the guard allows the forum (owned →
  allowed); a refused post writes the events equivalent of `NOTIFY_SKIPPED_KIND` and the review card falls back to
  the test channel as today (that is the one fall-back that stays, because it is the test policy, not a mode).

## D. Site

The events page's settings block gains the two keys (the channel picker shows `# name · Category`) and **Make the
forum** (`POST /api/events/forum`, staff, mirroring `POST /api/requests/forum`); the event row on the page links the
post where it linked the room. Mock rows, contract, labels, `check.mjs`.

## E. Tests (mirror the package)

`tests/test_events.py`: `review_place` on a room row, a post row, an old row with NULL kind; `open_review_post` builds
the right title / tags / view; the refusals' words; `tests/cogs/community/test_events.py`: propose in forum mode makes
a post and stores kind `post`; approve / deny / cancel / end edit the tag and archive; **Delete this post** deletes
and settles; the cancel-on-gone sweep ignores an archived post and cancels on a deleted one; retention archives
instead of deleting; test-mode deletes 5 minutes after the end; a blank forum refuses Propose in words; open rooms
survive a mode flip; the host gets no overwrite in forum mode; `tests/api/tools/test_events.py`: the route;
`tests/storage/test_db.py`: schema 45; the count guards (keys, routes, core settings if any). Both `pytest -n 8`
orders (`BB_REVERSE=1`), `ruff check .`, the ES-module parse, `node site/mock/check.mjs`, `discordmd.test.mjs`,
`labels.test.mjs`, with the bot-shaped env cleared (`gotchas.md`; the name list is in `scripts/scan/clearenv.ps1`).
⚠️ KI-26: a stalled pytest is killed by its own process TREE only.

## F. Docs

`code-notes.md`; this doc's `## Deviations` (dated) and `## What was NOT verified`; `architecture.md` (schema 45, keys,
routes); `docs/info/README.md` row; `sweeps.md` rows `EF-a…` (a: Make the forum from `/event`; b: propose → the post
with the card and buttons, tagged pending; c: approve → tag + the announcement as before; d: deny → tag + archived;
e: Delete this post; f: a mode flip leaves an open room alone; g: the events page's link opens the post); the events
guide gains one fact line. NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`.

## H. Move an open event's room into the forum (owner, 2026-09-17 22:1x) — ✅ LIVE as v137 (release `a16f5e5`, merge `43ec005`, 2026-09-17 23:00; the `### §H` deviations at the foot are the truth; sweeps 603–607; verified: boot clean (logged in 23:00:11), /health ready; Move to the forum pressed on the events page 23:0x for event #5 (the pending 'What Day It Was') → POST /api/events/5/forum 200; by token the forum holds post 'What Day It Was · 2026-10-03' (1550386189759156336) tagged pending with the opening line + card + Approve / Deny / Not an event — make it a request and the Delete-this-post card, and the old room no longer exists (row 603 done); a member-made 'Bot Stuff · 2026-09-18' post already sat in the forum from the owner's own test (row 597 done by him).)

> **Status: BUILT** on branch `events-move-to-forum` off `main` `90252a6`, **2026-09-17**. ⚠️ Read the
> `### §H` block under `## Deviations` first — **eleven** things differ from what is written below, and
> deviations **§H-2** (the Delete-card button §H names is unreachable, so the reachable Discord door is
> the `/event` card), **§H-1** (`settle=False` became a shared `remove_place`) and **§H-4** (the route is
> not a `contract.json` row) are the ones that matter. **No schema change** — the move re-points the
> columns schema 45 already has, so `SCHEMA_VERSION` stays **45**. Registry **282 → 283**
> (`events_moved_line`); `pytest -n 8` **6755 → 6793**, green forward and under `BB_REVERSE=1`; mock
> unchanged at **20 pages / 187 routes**; `ruff check .` clean. Nothing has met Discord.

*"#pending-ds-poison-meter-pt-what-day-it-was convert this channel into a thread into events"* — event #1 (*What Day It
Was*, pending, its room made before v136). §C leaves open rooms as rooms on purpose; this adds the staff move for exactly
that case.

- **`move_room_to_forum(bot, guild, actor, row, *, via)`** in `events.py`: refuses in words when the row is not a room
  (`review_kind` post), when the event is settled (denied / cancelled / done), when `events_forum_channel_id` is blank or
  dead (names **Make the forum**), or when the guard refuses the forum. Otherwise: opens the post exactly as Propose does in
  forum mode (`open_review_post` — the opening line, the review card, the decision buttons, the tag for the row's CURRENT
  status, the Delete-this-post card), re-points the row (`review_channel_id` = the thread, `review_message_id` = the starter,
  `review_kind` = post, `card_channel_id` as forum mode sets it), posts ONE line in the old room (a key: `events_moved_line`,
  default *"This event now lives in its own post: {post}. This room is being removed."*, `{post}` = the thread mention),
  then deletes the room through the existing `delete_room` path WITHOUT settling the event (a new `settle=False` — or
  whatever shape keeps one deletion path; say so) and logs `event.room_moved` (event_id, from the room id, to the thread id,
  `via`). ⚠️ The room's earlier messages are not copied — Discord has no move for messages; the log row and the moved line
  name the room id so the history is findable in the audit log. The host's DM: none (they were never in a staff-side post).
- **Doors:** a **Move to the forum** button on the room's Delete card (`room_notice_view`, kind room — a second button,
  staff-gated by the same `may_delete_room` rule; renders only while `events_review_mode` is forum AND the forum is set),
  and **Move to the forum** on the site's event detail card (`POST /api/events/{event_id}/forum`, staff, mirroring
  `/room/delete`); mock, contract, `page-events.js`.
- **Tests:** the pure move (a room row → a post row, the tag matches status, the moved line, the deletion without settling,
  every refusal), the button renders only under forum mode, the route, the count guards. Docs: this section's deviations,
  `code-notes.md`, sweeps `EM-a…` (a: press Move to the forum on event #1's room → the post appears with the card and
  buttons tagged pending and the room goes; b: Approve inside the post works; c: the site's button on a settled event refuses
  in words).

## Deviations

> Written by the build, **2026-09-17**, on branch `events-forum` off `main` `a7399b0` (the design
> doc's own commit `3861e9c` plus one TODO line). Everything below is a place the build did NOT do
> what §A–§F says, and why. ⚠️ **Nothing here has met Discord**: no boot, no token, no forum made
> in a client, no post opened, no button pressed, no DM sent, and `TEST_MODE` was never flipped.
> The whole verification is `ruff check .` (clean), `pytest -n 8` (**6696 → 6755**, green forward
> and under `BB_REVERSE=1`), the ES-module parse of all **33** `site/public/assets/*.js`,
> `node site/mock/check.mjs` (*20 pages, 187 routes, 24 core settings, all keys present*),
> `node site/mock/discordmd.test.mjs` and `node site/mock/labels.test.mjs`. **No browser rendered
> the events page**, real or mock.

1. ⚠️ **The forum has SIX tags, where §A named five — and §A's own instruction is what produced
   the sixth.** §A says *"named exactly after `events.py`'s status constants … `events.py:79–84`
   is the list; match it one for one and say so"*. That list is `pending, approved, denied, live,
   done, cancelled` — **`live` is in it**, and the design's own table omitted it. A live event with
   no tag of its own would have gone on wearing **approved** for its whole duration, which is the
   one window where staff most want to see at a glance what is happening. `live` is 📣;
   `test_the_forum_carries_one_tag_for_every_status_an_event_can_hold` asserts the two lists are
   equal, so a seventh status cannot be added without a tag.

2. ⚠️ **`review_place` is SYNC and never calls `fetch_channel`, where §C names one.** §C asks for
   *"`guild.get_thread(id)` then `bot.get_channel(id)` then a `fetch_channel`"*. The requests
   precedent it names in the same breath — `thread_of` (`cogs/community/requests.py:363`) — does
   the first two and stops, because it is sync. Making this one async would have turned **ten**
   call sites into awaits for what is a cache read: `build_card`, `event_line`, `rename_channel`,
   `room_of`'s callers and the two sweeps. What a `fetch` would have bought is an archived post,
   and deviation 3 is why that case is handled differently anyway.

3. ⚠️ **An unresolvable POST is not counted as a miss and never cancels an event — deletion is
   `on_thread_delete`'s to report.** §C says *"a deleted post is `review_channel_deleted`, an
   archived post is NOT gone"*, and the only way to honour that is to stop `_recheck` deciding
   anything about a post it cannot see. Measured against discord.py 2.7.1: an archived thread
   leaves `Guild._threads`, so `guild.get_thread` answers `None` for it — and `default_auto_archive_duration`
   is **1440 minutes**, which means **any event proposed more than a day ahead would have had its
   post auto-archive and its event cancelled for being early.** So a post row re-owns when it
   resolves and does nothing when it does not; a new `on_thread_delete` listener carries the
   cancel, and the two-consecutive-misses rule (checklist 32) is untouched for rooms.

4. **The 1440-minute auto-archive is kept as §B asks ("the requests value"), and it is the reason
   deviation 3 exists.** Discord's maximum is 10080 (a week), which would have hidden the problem
   for most events rather than fixed it. Writing a message into an archived thread un-archives it
   where the bot has Manage Threads, so an approved event's go-live line brings its own post back.
   ⚠️ **Unmeasured:** that un-archiving has not been exercised against Discord.

5. ⚠️ **The retention sweep logs `event.post_archived`, NOT `event.channel_deleted`.** §C says
   *"writes the same log kind with `kind: post`"*. `event.channel_deleted` is read by an auditor as
   *a channel was removed*, and in live mode nothing is removed — the post is tagged and archived
   and keeps its id. A kind that claims a deletion that did not happen is the same defect
   checklist 2 exists to stop one class up. Under `TEST_MODE` a post IS deleted, and there the
   sweep writes `event.channel_deleted` exactly as a room does, with `kind: post` in the details.

6. ⚠️ **A guard-refused forum is refused in WORDS; there is no fall-back to the test channel.**
   §C's last bullet keeps one fall-back — *"a refused post … the review card falls back to the test
   channel as today"*. It is unreachable as written, and building it would have been worse than
   leaving it out. Unreachable: `forum_of` CLAIMS the forum on every read (§B's own rule), and
   `TestModeGuard.allows_channel` returns True for anything in `owned_channel_ids`
   (`guard.py:84–92`), so the check immediately after the claim cannot fail. Worse: the room path's
   fall-back stores the ROOM as `review_channel_id` while the card sits elsewhere — the post
   equivalent would have stored the FORUM, and **Delete this post** would then have offered staff
   the whole forum to delete. The path is kept as a refusal (`POST_REFUSED_TEST`, which names
   `event.post_skipped_test_mode`) so a future guard change is answered in words rather than
   silently.

7. ⚠️ **`rename_channel` passes its `status` ARGUMENT to `retag_post`, not the row's.** Found by a
   test, not by reading: `_finish` calls `rename_channel(..., DONE, ...)` with the row it read
   **before** `set_status`, so tagging from `row["status"]` marked a finished event **live**. Rooms
   never had this bug because `channel_name(status, …)` already took the argument.

8. **`cancel_event` re-tags the post itself, because it is the one status change that does not
   rename.** `cancel_for` renames afterwards and `_cancel` (the reconcile path) does not, so a
   reconcile-driven cancel would have left a cancelled event tagged **pending** for ever. The
   double call on the `cancel_for` path costs nothing: `post_is_right` compares the tags and the
   archive flag and skips the edit.

9. ⚠️ **A settled post is NOT disowned at the archive, where `requests.retag_post` disowns.** A
   test post still has to be DELETABLE by the five-minute sweep, and `allows_place` reaches that
   through `owns_channel` (`guard.py:103`). The set therefore grows by one entry per settled event
   until the process restarts; that is the same shape rooms already have (they are disowned only
   at the delete), and it is bounded by the sweep.

10. ⚠️ **Every word the bot posts is still a CONSTANT in `events.py`, not a settings key.** The
    standing rule (owner, 2026-09-17) says a heading, a line and a button label are each a settings
    key. This build introduced the post's opening line, the post notice and six refusals as
    constants beside the room twins they mirror, because §A names exactly two keys and the events
    feature has ~50 such constants today — keying only the new ones would have left the feature
    half-keyed and the two halves of one sentence in two different homes. **This is named as a
    departure, not as a decision**: the honest fix is one pass that keys the events vocabulary as
    `frontdoor_*` did, and it is bigger than this build.

11. **`black_bloc/forums.py` is a NEW shared module, which §B allowed for ("share a helper if one
    falls out cleanly — say so").** Three things fell out cleanly and are now single-homed:
    `tag_named`, `forum_tags(names, emoji)` and `forum_overwrites(guild, category)`, plus
    `AUTO_ARCHIVE_MINUTES`. `black_bloc/requests.py` and `cogs/community/requests.py` import them;
    `requests.forum_tags` keeps its name and its default so nothing reading it changed, and the
    requests suite is green unchanged. What did NOT fall out cleanly is `make_forum` itself — the
    refusal sentences, the key, the log kind and the tag set are all feature-specific, so
    `events.make_forum` is a copy of its shape rather than a call into a shared one.

12. **The two keys reach a FOURTH door as well as the three §A named.** Registry + mock row +
    label, and also `events.SETTINGS_KEYS`, so `/event` ▸ Settings ▸ Rooms… ▸ **Forum…** writes
    them through the same `write_settings` path every other events key uses. The events page needed
    nothing: it already draws the whole `events` namespace through `namespaceSettings`.

13. **`build_forum` is a FIFTH sub-page rather than two more rows on Rooms…** A Discord view takes
    five rows and a select fills one; Rooms… already spends rows 0–2 on three selects and row 3 on
    its buttons. The same reasoning that put Rooms… on its own page in `events-rooms-design.md`
    deviation 3.

14. ⚠️ **`pytest -n 8` did not stall once** (KI-26). Six full runs in this worktree — the baseline,
    four after code, and the `BB_REVERSE=1` one — all finished in 55–80 s. The count stands at
    seven, and none of these was a `deploy.ps1` run.

15. **What this build deliberately did NOT touch.** `docs/TODO.md`, `docs/DONE.md`,
    `docs/deploys.log` and `docs/KNOWN_ISSUES.md`. No setting was flipped: `events_review_mode`
    ships **room** and `events_forum_channel_id` is blank, so **every forum path here is
    unreachable until the owner makes the forum and flips the mode.** Hand-made posts in the events
    forum are NOT adopted — §C says so and the bot ignores a thread no row claims. Nothing was
    merged, deployed or pushed to `main`.

### §H — moving an open room into the forum

> Written by the build, **2026-09-17**, on branch `events-move-to-forum` off `main` `90252a6`.
> Everything below is a place the build did NOT do what §H says, and why. ⚠️ **Nothing here has
> met Discord**: no boot, no token, no button pressed, no post opened in a client, no room
> deleted, and `TEST_MODE` was never flipped. The whole verification is `ruff check .` (clean),
> `pytest -n 8` (**6755 → 6793**, green forward and under `BB_REVERSE=1`), the ES-module parse of
> all **33** `site/public/assets/*.js`, `node site/mock/check.mjs` (*20 pages, 187 routes, 24 core
> settings, all keys present*), `node site/mock/discordmd.test.mjs` and
> `node site/mock/labels.test.mjs`. **No browser rendered the events page**, real or mock.

**§H-1.** ⚠️ **`settle=False` on `delete_room` became a shared `remove_place` helper** — §H allowed
this ("*or whatever shape keeps one deletion path; say so*"). A flag would have had to turn off
**two** things, not one: the cancel *and* the `set_review(bot.db, id, None, …)` that clears
`review_channel_id` — which the move has just pointed at the new post, so clearing it would have
thrown the post away. `remove_place` is the guard check, the delete, the disown and nothing decided
about the row; `delete_room` keeps its own cancel, its own `set_review` and its own
`event.channel_deleted` row, so its log rows, its details and its sentences are unchanged.

**§H-2.** 🔴 **The button §H puts on the room's Delete card is UNREACHABLE, so the reachable Discord
door is the `/event` panel's event card instead.** §H says *"a **Move to the forum** button on the
room's Delete card (`room_notice_view`, kind room … renders only while `events_review_mode` is forum
AND the forum is set)"*. That card is posted **once, at propose time** (`submit_event` →
`post_room_notice`), and at propose time the two conditions cannot both hold: in `room` mode the
gate is False, and in `forum` mode the proposal gets a POST, so the card is a post's card and its
kind is not `room`. Worse for the owner's actual case — event #1's room was made **before** v136 —
a message already in Discord keeps the components stored on it; nothing re-renders an old notice, so
no edit to `room_notice_view` could ever reach it. The button is built exactly as §H describes
(`moving_notice_view` asks the mode and the forum) **and** added to `build_card`, the `/event`
panel's own event card, which is the only Discord surface that is drawn fresh every time. That is
where the owner presses it for event #1, gated on `may_move_to_forum` AND `may_delete_room`. This is
the same defect class as deviation 6 of the parent build, caught before it shipped rather than after.

**§H-3.** **The move logs ONE row, `event.room_moved`, and no `event.channel_deleted`.** §H names
only `event.room_moved`, and the room's removal is what its `from` field is for. A second headed row
for one web write is what checklist 34 exists to stop; the `would_delete_channel` and
`room_delete_failed` rows `remove_place` writes when it cannot delete are unchanged, because those
are failures and a failure must never be silent.

**§H-4.** ⚠️ **`POST /api/events/{event_id}/forum` is NOT a `contract.json` row, so the table stays at
187 routes while the real API serves 188.** `site/mock/check.mjs`'s `checkRoutes` calls `seed()`
before **every** entry, and a fresh seed has no forum — the move would answer its own 409. Seeding a
forum instead would make the entry that *makes* the forum refuse as already-there, so one row cannot
be bought without losing another. Instead: a bespoke `checkEventsMove()` pass (the `checkPostsModes`
precedent) walks *no forum → 409*, the move → 200 with the keys and `review_kind: post` and the
status still `pending`, a second press → 409, and a settled event → 409; `checkActionKinds` presses
the route so `web.event.room_moved` is proved listed; and `tests/api/tools/test_events.py` covers the
real router with **10** tests. That is more than a contract row would have asserted, and it is named
here because the route count in `architecture.md` no longer equals the router count.

**§H-5.** **`move_room_to_forum` does NOT check `events_review_mode`; only the doors do.** §H lists
four refusals and the mode is not among them, so staff who reach the route while the mode is still
`room` may move an event into a forum that exists (staff final say, owner 2026-09-03). The rendering
gate, `may_move_to_forum`, DOES include the mode exactly as §H says, so no button offers the move
outside forum mode. Two different questions, kept apart on purpose.

**§H-6.** **A room whose id no longer resolves is still moved, not refused.** `room_of` can answer
`None` on a stale id. The post is opened and the row re-pointed; the moved line and the deletion are
skipped and the sentence says only where the event went. Refusing would have stranded the event in a
room that is not there. A row with **no** `review_channel_id` at all is refused in words
(`MOVE_NO_ROOM`) — there is nothing to move.

**§H-7.** **The signature gained two view factories: `move_room_to_forum(bot, guild, actor, row, *,
review_view=None, room_view=None, via=VIA_DISCORD)`.** §H names only `via`, but a post has to be
opened with its Approve/Deny buttons and its Delete-this-post card, and those live in the cog —
`submit_event` already takes the same two. The website route imports them inside the function body,
the way `handoff.py` imports the requests cog, because a post with no view is a post staff cannot
decide from.

**§H-8.** **It returns a `panels.Outcome`, not a `(said, ok)` pair.** §H does not say. `Outcome`
carries the code and the HTTP status the route needs, and `make_forum` beside it already returns one;
the `(said, bool)` shape belongs to `delete_room`, which the site translates into a 409 by hand.

**§H-9.** **`events_moved_line` got a validator §H did not ask for.** `settings_store.checked_moved_line`
refuses any placeholder but `{post}` in words, and `moved_line` ALSO catches `Exception` around
`.format` and falls back to the default with a log line (checklist 17). Two halves of one rule: the
door refuses the typo, the renderer survives one that got in before the door existed. The line may be
written with no `{post}` at all — a room being closed is allowed to say so without a link.

**§H-10.** ⚠️ **Only the moved line is a settings key; the six refusals, the button label and the
success sentence are still CONSTANTS.** The standing rule (owner, 2026-09-17) says every word the bot
posts is a key, and §H names exactly one. Deviation **10** of the parent build stands unchanged and
this build did not widen it: keying eight more sentences would have left the events vocabulary
three-quarters unkeyed with the halves of one paragraph in two different homes. Named as a departure,
not a decision — the honest fix is still one pass over the whole events vocabulary.

**§H-11.** **What this build deliberately did NOT touch.** `docs/TODO.md`, `docs/DONE.md`,
`docs/deploys.log` and `docs/KNOWN_ISSUES.md`. **No setting was flipped and no schema change was
needed** — the move writes the columns schema 45 already has (`review_channel_id`,
`review_message_id`, `card_channel_id`, `review_kind`), so `SCHEMA_VERSION` stays **45** and there is
no migration to run before the deploy. Nothing was merged, deployed or pushed to `main`. ⚠️ **`pytest
-n 8` did not stall once** (KI-26): four full runs in this worktree — the baseline, two after code
and the `BB_REVERSE=1` one — all finished in 53–82 s, none of them a `deploy.ps1` run.


## What was NOT verified

- **Nothing met Discord.** No boot, no token, no forum created in a guild, no post opened, no tag
  applied, no button pressed in a client, no DM sent. `TEST_MODE` was never flipped and nothing was
  deployed. Sweep rows `EF-a`…`EF-g` in [`../access/sweeps.md`](../access/sweeps.md) are all unrun.
- **The migration was not run against a copy of the live database.**
  `tests/storage/test_db.py` asserts `SCHEMA_VERSION == 45` and the column is added by the same
  `ADDED_COLUMNS` pattern every additive column in this repo uses, but the live file was not
  touched.
- ⚠️ **"A forum can be made in this guild" is still inference**, exactly as
  `blackmail-threads-design.md` deviation 12 recorded it: no forum has ever been created in the
  live guild by Black Bloc. What WAS read off the installed **discord.py 2.7.1**:
  `Guild.create_forum` takes `available_tags` and `default_auto_archive_duration`;
  `ForumChannel.create_thread` returns a `ThreadWithMessage` (`thread`, `message`) and takes
  `applied_tags`; `Thread.edit` takes `applied_tags` and `archived`; `Thread.category_id` is the
  parent's; and an archived thread leaves `Guild._threads`, which is deviation 3's whole basis.
- **No `DynamicItem` has survived a real restart.** The **Delete this post** button is the same
  `DECISION_TEMPLATE` registration the room button already uses, rebuilt from its custom id in a
  test with fakes. ⚠️ Its LABEL is not in the custom id, so a button rebuilt by `from_custom_id`
  reads "Delete this room" — that object is only ever used for the CALLBACK, and the label Discord
  renders is the one stored on the message, but no restart has proved it.
- **No browser saw the events page**, real or mock; the site half was exercised only by
  `node site/mock/check.mjs`, `tests/api/tools/test_events.py` and the ES-module parse.
- **The auto-archive round trip is untested**: that a message into an archived post un-archives it
  (deviation 4), and that Discord actually drops an archived thread from the cache on a running
  bot rather than only in the library's source (deviation 3).
- **`review_place` was not exercised against a restarted process.** The claim-on-every-read rule is
  proved by a test asserting the guard's owned set, not by a restart.

### §H — moving an open room into the forum

- **Nothing met Discord.** No boot, no token, **Move to the forum** was never pressed in a client,
  no post was opened by a move, no room was deleted, no `events_moved_line` was ever read in a
  channel. `TEST_MODE` was never flipped and nothing was deployed. Sweep rows `EM-a`…`EM-e` in
  [`../access/sweeps.md`](../access/sweeps.md) are all unrun.
- ⚠️ **The owner's own case — event #1's room, made before v136 — was not exercised against the
  live database.** The move was proved against fakes and against the mock; the live row's
  `review_kind` is NULL (schema 45 default) and reads as a room, which is what the move needs, but
  nobody has read that row.
- ⚠️ **Deviation §H-2's claim that an old notice card cannot gain a button is LIBRARY REASONING,
  not a measurement.** It follows from Discord storing components on the message and from nothing
  in this repo re-rendering `post_room_notice`'s message (`post_room_notice`'s id is not stored) —
  but no client was opened to look at event #1's card.
- **No browser saw the events page**, real or mock. The site half was exercised only by
  `node site/mock/check.mjs` (including the new `checkEventsMove` pass),
  `tests/api/tools/test_events.py` and the ES-module parse — so the **Move to the forum** button on
  the queue row has never been drawn.
- **The `/event` panel card's row 2 was not seen in Discord.** The button is added at `row=2` on the
  reasoning that rows 0 and 1 are already spoken for; a view that exceeds five rows raises at send
  time, and only a real panel would prove it does not.
- **The API route's lazy cog import was not exercised in the running process** — only under pytest,
  where the cog module is importable. A deployment where `black_bloc.cogs.community.events` failed
  to import would fail the route rather than the boot.

