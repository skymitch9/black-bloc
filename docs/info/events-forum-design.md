# Events as a forum under BlackMail — one post per event, like requests and modmail

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatched to Opus 2026-09-17 21:22
> as branch `events-forum`**. **Last verified: 2026-09-17 21:2x** against `main` `0707768` (v135): `black_bloc/events.py`
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

## Deviations

*(the build agent writes here what it had to do differently, dated)*
