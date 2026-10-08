# Marathon runner posts — each BaF run its own pinned post in the marathon's thread; the board is a head

> ⚠️ **Superseded in part 2026-10-08 (marathon controls, branch `marathon-controls-a`):** a run's post carries one button a person, without "for this run", one row of five before a menu; the No-@ pair lives in the People view; state lines only for exceptions (D7). See [`marathon-controls-design-2026-10-08.md`](marathon-controls-design-2026-10-08.md); the text below is left as it was decided.

> **Audience:** the conductor, reviewers, and the next session touching marathon boards, threads or pins.
> **Status:** TRACKED · 🔨 **BUILT on branch `marathon-runner-posts` (off `main` `997c0be2`, v177 live), NOT merged, NOT
> deployed.** Schema **73 → 74**, registry keys **574 → 578**, routes unchanged (**264**), five new log kinds plus two
> shadow twins and three `_failed` kinds; deviations below.
> **Last verified: 2026-09-26** — against the branch's own code by the tests (`tests/cogs/content/test_marathon_runner_posts.py`,
> `tests/test_marathon_runner_posts.py`, the board-head test in `tests/test_marathon.py`, the schema-74 test in
> `tests/storage/test_db.py`), the whole suite, and `check.mjs` on a worktree mock (`MOCK_PORT=8817`: *22 pages, 264 routes,
> 25 core settings, all keys present*). ⚠️ **NOT checked:** anything against Discord (a post, a pin, the 50-pin cap, an edit
> in a forum-post thread), the live database and its migration, SS4C's live rows (whether champrul's run is still to come,
> on, or done at the deploy); the bot was never run and no page was rendered in a browser. Secret NAMES only.

## The asks, verbatim (owner, 2026-09-26 20:1x–20:2x Phoenix)

1. *"When we highlight a BaF runner have it be a separate post and not part of the original post"*
2. *"Sorry in the marathon thread for today's event Champrul was mentioned in the thread post"*
3. *"Perfect and we can then pin those messages"*

The *original post* is the marathon's **board** — the pinned message at the top of a tracked marathon's thread
([`marathon-schedule-design.md`](marathon-schedule-design.md) §D) — which listed one line per BaF run, champrul's among
them for SS4C.

## As built

**The board is a head.** With `marathon_runner_posts` on (the default), `Marathons.board_words` passes `lines=False` to
`marathon.board_text`: the board is `marathon_board_template` alone — marathon, BaF count, dates, the channel/schedule link —
and, while nobody from BaF is found, `marathon_board_empty_line` under it. It is still ONE message, edited in place and pinned
exactly as before (`marathon_pin_board`, off a day after the marathon ends). With the key **off**, the board is the old board
with one `marathon_board_line_template` per run and no runner post is made.

**One post per BaF run** (`cogs/content/marathon_runner_posts.py:sync_posts`). `Marathons.sync_board` is now the board message
(`sync_board_message`, the old body, unchanged) and then `sync_posts`, so every door that already refreshes the board — the
fetch, `follow` on the tick, Post the board, pair/unpair, Shout it now, Mark done/upcoming/live, Track — also syncs the posts.
The posts follow the board's rules and only run when the board succeeded and exists: tracked marathons only (untracked posts
nothing), `marathon_mode` off posts nothing, shadow sends them to the rehearsal home with the rehearsal note like every other
marathon post (`_send`), and they go where the board goes (`_place` — the thread, or `marathon_channel_id` for a marathon
tracked without one).

- **Which runs:** `marathon_runner_posts.wanted` — every run that already has a post, and every run of ours (the board's
  `is_ours` rule, unchanged: a linked or paired person on it, hosts/commentators as `marathon_match_hosts` says) that is
  upcoming, live or done. A run dropped before it was ever posted gets nothing. **Schedule order** (`scheduled_at`, then
  `order_no`), so the first tick after the deploy backfills an already-matched marathon's runs top to bottom.
- **Words:** `marathon_runner_post_template` (default
  `**{runner}** ({mention}) {part} **{game}** — {category} · {when} ({relative}) · {state} · <{url}>`), fields `{runner}`
  (the BaF person's schedule name; the schedule's runner names once nobody from BaF is on it), `{mention}` (`<@id>` as text),
  `{game}`, `{category}`, `{part}`, `{when}` / `{relative}` (Discord `<t:…:f>` / `<t:…:R>`), `{url}` (the marathon channel's
  Twitch, else the runner's own, else the schedule — `marathon.run_url`, the reminders' rule), `{marathon}`, `{state}`.
  `{state}` is the existing `marathon_state_*` word (help text now says *board and a run's own post*), or the new
  `marathon_runner_post_unlisted` once staff unlink the runner so nobody from BaF is on it. A template that will not fill
  falls back to the shipped words (checklist 17).
- **Never pings:** every send and edit is `AllowedMentions.none()` — the member is named, not pinged.
- **Edited in place** when its words change: the slot moves (`{when}`), it goes live, it is done, it is dropped (edited to
  *off the schedule*, never deleted), it comes back, or it is unlisted. What was last written is remembered per run in memory
  (`cog.posts_sent`), so an unchanged tick costs no Discord call; after a restart each post is fetched once and compared by
  content (the board's own `endswith` rule). A post a person deleted is posted again (the board's rule), as long as the run
  still gets one.
- **Stored per run:** `marathon_runs.post_message_id`, `post_channel_id`, `post_pinned` (schema 74 — Deviation 1).

**Pinned.** A post is pinned right after it is posted (`pin_one`) when `marathon_runner_posts_pinned` (bool, default on), the
mode is **on** (the board is not pinned in shadow either), the marathon is not a day past its end, and the run is not already
past its own grace (a done run backfilled two days late is posted, not pinned). The pin logs `marathon.runner_post_pinned`.
A refusal for **Discord's 50-pin cap** (error code 30003) logs `marathon.runner_post_pin_capped` (IMPORTANT) **once per
channel per boot** and carries on — the post stays. Any other refusal is `marathon.runner_post_pin_failed`.

**Unpinned** (`unpin_one`, the board's `unpin_board` shape: the stored flag cleared first, then the pin taken off only when the
message carries one — checklist 3):
- **per run, a day after it is over** — `unpin_because`: a done run one day after its scheduled end (`AFTER_END`, the board's
  own grace, applied to the run), a dropped run one day after the schedule last listed it (`last_seen_at`); a run nobody from
  BaF is on any more comes off at once (`because: unlisted`);
- **all of them with the board** — `unpin_board` now calls `unpin_posts` first, so untrack (`untracked`), archive
  (`archived`), the day after the marathon (`over`) and a thread move (`moved`, the old thread's posts only) take every
  runner-post pin off where the board's comes off.
- These checks run on **every tick for every marathon** (`unpin_due`, in `tick_marathon` and in the mode-off branch of
  `tick_once`), whatever the mode, the posts key or the pinning key say — checklist 38: an in-flight pin is carried to its end.

**Thread move (v177).** `move_thread` unpins the runner posts that sit in the old thread (beside the board's unpin), archives
the old thread as before, and the next `sync_board` — the same tick — posts the board fresh in the new thread and then each
runner post fresh under it (a post whose stored channel is not the post place is posted again), pinned under the usual rule.
The old posts stay in the archived old thread, unpinned.

**Unchanged:** the shoutout stays its own message (`shout`, its own template and id), reminders, the opening line and the
control message; untracked marathons post nothing; shadow routes as today.

**Keys (four, Marathons group, registry + mock row + label):** `marathon_runner_posts` (bool, on — off = the old board with
lines, checklist 33), `marathon_runner_posts_pinned` (bool, on), `marathon_runner_post_template` (text), and
`marathon_runner_post_unlisted` (text). Five existing keys changed help text only: `marathon_board_line_template` (*used only
while marathon_runner_posts is off*) and the four `marathon_state_*` words.

**Log kinds:** routine `marathon.runner_post_posted`, `runner_post_edited`, `runner_post_pinned`, `runner_post_unpinned`
(`because`: `run_over` / `unlisted` / `over` / `untracked` / `archived` / `moved`); shadow `marathon.would_post_runner_post`,
`would_edit_runner_post`; IMPORTANT `marathon.runner_post_pin_capped`, and by suffix `runner_post_failed` (`step: post | edit`),
`runner_post_pin_failed`, `runner_post_unpin_failed`.

## Deviations

1. **Three columns, not one** (`marathon_runs.post_message_id INTEGER`, `post_channel_id INTEGER`, `post_pinned INTEGER NOT
   NULL DEFAULT 0`; schema **73 → 74** through `ADDED_COLUMNS`, mirrored to `marathon_runs_archive` by the boot rule). The
   channel is needed because a moved thread leaves posts in the old one (the shout stores `shout_channel_id` for the same
   reason); the pinned flag lets the tick decide what to unpin with a DB read only, instead of fetching every post every
   minute. Additive; no backfill — every row reads empty until the first tick posts.
2. **The per-run line keys are NOT retired.** `marathon_board_line_template` is still live — it is the board's line when
   `marathon_runner_posts` is off (the brief's part 5) — so its help text says so instead of *retired*. The four
   `marathon_state_*` words are **reused** by the posts rather than duplicated (one fact, one home); only the *unlisted* word is
   new, because the board never had that state.
3. **A run already done is posted (backfill included); a run dropped before it was posted is not.** The board listed both;
   a fresh post for a run the schedule has thrown out would only ever say *off the schedule*. A done run inside its day's grace
   is pinned; past it, posted unpinned.
4. **A run staff unlink (nobody from BaF on it) keeps its post**, edited to `marathon_runner_post_unlisted`, and its pin comes
   off at once. Deleting it would be the only message the feature ever deletes, and staff can delete it by hand.
5. **Nothing is pinned in shadow** — the board's existing rule (`sync_board_message` pins only when not shadow), mirrored.
6. **The 50-pin cap is logged once per CHANNEL per boot** (`cog.pin_capped`), not once ever: a new boot, or another marathon's
   thread, logs again. Discord's refusal is recognised by its code (30003) only.
7. **A post that cannot be fetched is posted again** — the board's rule. A transient fetch failure (not a NotFound) can
   therefore duplicate a post, as it can the board today.
8. **After a restart the first tick fetches each posted run's message once** to compare it (the in-memory cache is empty) — one Discord read per run that
   has a post (SS4C: champrul's, per the brief; not counted here).
9. **The board's `{count}` still counts every BaF run on the schedule** (done and dropped included), exactly as before; only the
   lines left.
10. **The thread-move re-post covers the runs that would be posted new** (ours, upcoming/live/done); a dropped run's old post
    stays in the archived old thread and is not re-posted.

## What was NOT verified

- ⚠️ **Nothing met Discord.** Posting, pinning, the pin cap refusal (code 30003 was taken from Discord's documented error list,
  not observed), editing a post in a forum-post thread, and unpinning in a thread about to be archived were exercised against
  the suite's fakes only.
- ⚠️ **The live migration (schema 74) has not run**, and SS4C's rows were not read: whether champrul's run is upcoming, live or
  done at the deploy — which decides whether its post says *coming up*, *on now* or *done*, and whether it is pinned — is the
  conductor's to read. Nothing else of ours on SS4C was counted.
- **The 2,000-character cut** of a post (the template is staff text) is enforced by slicing; a post that long was not tested.
- **No site surface changed** beyond four Settings rows and five help texts; nothing was rendered in a browser — the mock
  was checked by `check.mjs` and a `GET /api/settings` read only.
