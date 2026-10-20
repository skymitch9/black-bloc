# Weekly questions — a queue the owner posts from, with the bot as the safety net

> **Audience:** the build agent (branch `weekly-questions`), reviewers, and the session that sets up
> the owner-side Claude task. **Status:** TRACKED · 🔨 BUILT on branch `weekly-questions`, NOT merged, NOT deployed (2026-10-19);
> designed 2026-10-19 15:3x Phoenix, all four forks decided by the owner. See *Deviations* at the end. **Last verified: 2026-10-19** — nothing here is measured yet; the
> code shapes named are the birthdays feature's (`black_bloc/birthdays.py`,
> `black_bloc/cogs/community/birthdays.py`, `site/public/birthdays.html`) read as the reference pattern,
> not re-traced line by line. ⚠️ NOT checked: whether an unattended scheduled Claude run can drive
> Claude in Chrome (the owner-side half, §7).

## The ask (owner, 2026-10-19, verbatim)

*"we need a feature to post questions to a channel once a week 9am (changeable) on Monday
(changeable). I also want it to post from my personal discord account and then if that fails fall
back to having the bot post the question. I want to be able to load up a list of questions ahead of
time for multiple weeks in a row in queue"*

Then the owner's own design: *"What if we have a Claude work task to post the questions weekly. Then
we build a bot function that check for the weeks question … and if my account didn't post it the bot
does. My account could post at 9:00 and the bot verifies it's there by 9:05"*.

## Decisions

| Fork | Decided | Owner's words |
|---|---|---|
| 1 — post as the owner | A scheduled Claude task on the owner's PC posts from his account; the bot checks after a grace window and posts itself if the question is not there. Owner accepted the Discord ToS / ban risk of the Claude half knowingly. | "Yes risk it" |
| 2 — queue runs dry | The week is skipped; the bot warns ahead (DM + log channel) | "A" |
| 3 — reply thread | No thread. Still a settings key (configurable-both-ways rule), default OFF | "B" |
| 4 — one queue or several | One queue, one channel, one day + time | "A" |

## 1. The queue (bot-owned, one home)

Table `weekly_questions` (new schema version): `id`, `position` (order in the queue), `body` (the
question text), `status` (`queued` / `posted` / `skipped` / `removed`), `slot_at` (UTC instant of the
slot it was used for, null while queued), `posted_by` (`owner` / `bot` / null), `channel_id`,
`message_id`, `added_by`, `added_at`, `resolved_at`. Next question = lowest `position` with status
`queued`. History is the non-queued rows, newest first.

## 2. The slot

Settings keys (registry + help + mock row + label, every one on the Settings page):

| Key | Type | Default |
|---|---|---|
| `question_mode` | enum off / shadow / on | **shadow** (checklist: anything that posts ships shadow) |
| `question_channel_id` | channel | unset |
| `question_shadow_channel_id` | channel | blank = global `shadow_channel_id` (the per-feature rehearsal home pattern) |
| `question_weekday` | enum monday…sunday | monday |
| `question_time` | HH:MM in `default_timezone` | 09:00 |
| `question_grace_minutes` | int | 5 |
| `question_owner_user_id` | user id | the owner's id (the account expected to post) |
| `question_template` | text, `{question}` | `{question}` |
| `question_thread` | bool | false |
| `question_thread_name_template` | text | `{question}` clipped |
| `question_warn_days` | int | 3 |
| `question_warn_dm` | bool | true (DM the owner user) |
| `question_warn_template` | text | the empty-queue warning wording, `{day}` `{time}` |

The slot is the next `question_weekday` at `question_time` in `default_timezone`.

## 3. Resolving a slot (the loop)

At `slot + grace` (and on every boot / tick afterwards until resolved, up to a 24-hour catch-up
window; past that the slot is logged as missed and never posted late):

1. Under a lock, re-read the week's row (checklist 37 — a reconcile that posts runs under a lock and
   re-reads its stored id).
2. No queued question → status nothing to post; log `question.skipped_empty` once per slot.
3. Look in the target channel (the real one when `on`, the rehearsal home when `shadow`) at messages
   since `slot - 15 min` by `question_owner_user_id` whose normalised text contains the normalised
   question (casefold, collapse whitespace, strip markdown emphasis characters). Found → mark
   `posted` / `posted_by=owner` / that `message_id`; log `question.posted_by_owner`.
4. Not found → the bot posts `question_template` there; mark `posted_by=bot`; log
   `question.posted_by_bot` with the reason (*owner's post not seen by HH:MM*).
5. `question_thread` on → open a thread on whichever message stands (the owner's or the bot's).

`off` resolves nothing and posts nothing.

## 4. The empty-queue warning

When the next slot is within `question_warn_days` and nothing is queued for it, once per slot: DM
`question_owner_user_id` (if `question_warn_dm`) and post a line in the log channel, both from
`question_warn_template`. Log `question.warned_empty`. A DM that fails is an `error.*` row, never
silent.

## 5. Staff moves (staff final say)

On the page and the panel: add (one, or **many at once — one question per line**, the "load up
several weeks" path), edit, remove, move up/down, **Post now** (resolves the current slot with the
bot posting immediately — superseded 2026-10-19 by **Post one now**, Deviation 14), **Skip this week** (the next question stays queued; the slot is marked
skipped), and for a bot-posted question **Take it down** (deletes the bot's message, puts the
question back at the top of the queue). A question the owner's account posted is never deleted by
the bot.

## 6. Surfaces

- **`/questions`** — one staff command opening an ephemeral panel: next slot (Discord timestamp),
  next question, queued count, buttons Add (modal, multi-line), Queue… (select → edit / remove /
  move), Post now, Skip this week. Buttons render only when valid.
- **The Weekly questions section of the Posts page** (`posts.html#sect-questions`; was `site/public/questions.html` until the 2026-10-19 move below) — the queue (drag or up/down to reorder, inline edit, remove),
  a paste-many add box, the history (posted by you / by the bot, link to the message), and the
  feature's settings section. No nav entry of its own. No explaining blurbs.
- **`GET /api/questions/current`** — operator-token readable: `{slot_at, question_id, body,
  rendered, channel_id, guild_id, channel_url, mode}` with `channel_url` the
  `https://discord.com/channels/<guild>/<channel>` link of the TARGET channel (rehearsal home while
  shadow). This is what the owner-side task reads. Empty queue → `body: null`.

## 7. The owner-side half (not part of the bot build)

A scheduled task on the owner's PC at `question_time` on `question_weekday`: read
`/api/questions/current`, open `channel_url` in Chrome (his logged-in Discord), type `rendered`,
send. Set up AFTER the bot ships, by the conductor with the owner. ⚠️ Unproven that an unattended
run can drive Claude in Chrome; if it cannot run, the bot covers the week, so nothing is lost.

## Not built

Several queues; recycling used questions; reply threads by default.

## Deviations

Recorded by the build (branch `weekly-questions`, 2026-10-19). Each is what the code does and why.

1. **A second table, `weekly_question_slots`** (one row per server and slot, `PRIMARY KEY (guild_id, slot_at)`). §1 named only `weekly_questions`, but "once per slot" (the empty-queue warning, `skipped_empty`, `missed`) and "Skip this week" must survive a restart, and a slot with no question has no question row to carry it. Statuses: `pending`, `posted`, `skipped`, `skipped_empty`, `missed`, `taken_down`. `weekly_questions` also carries `guild_id` (every table here is per server).
2. **`missed` is logged only for a slot the bot met before it passed.** The loop writes the NEXT slot's row as `pending` the first time it sees it. A slot already past `question_catchup_hours` with no row (the first deploy, or the feature switched on mid-week) is silent rather than reported missed — checklist 43's rule that an empty value means "the clock starts now".
3. **The 24-hour catch-up is a setting**, `question_catchup_hours` (1–72, default 24), per the configurable-both-ways rule.
4. **No `question_panel_minutes`.** A 26th `*_panel_minutes` key breaks the `/settings` panel-minutes select (25 cap, pinned by `tests/test_settings_panel.py`). `/questions` borrows `posts_panel_minutes`, the way points borrows `pb_feed_panel_minutes`.
5. **`question_mode` is not in `command_visibility.HIDDEN_WHEN_OFF`.** The mode block on `/settings` is one select at its 25 cap. `/questions` is staff-only (`STAFF_ONLY`) and its panel says `Mode — off` and offers no Post now while off.
6. **Every `question_*` key and every `question.*` log kind sit under `core`.** A `question` namespace or log FEATURE would be the 26th `/settings` group (same reason as pb_feed, brackets, points). The page reads core keys by the `question_` prefix.
7. **`question_owner_user_id` ships blank.** No owner id exists in config or settings (only Discord's `guild.owner_id`, which is not necessarily the owner). Blank means the bot posts every week; the panel and the page say so in one state line.
8. **Shadow warnings.** In `shadow` the empty-queue line goes to the rehearsal home and the DM is not sent (the row records `dm: "shadow"`); in `on` it goes to `log_channel_id` and the owner is DMed. A failed DM writes `error.dm` (a new IMPORTANT kind under `core`, not one of the four interaction `ERROR_KINDS`).
9. **Extra kinds:** `question.unskipped`, `question.requeued` (Put back a removed question), `question.post_failed` (no channel / Discord refused, once per distinct reason per slot), `question.thread_failed`. In shadow the bot's post is still `question.posted_by_bot` with `mode: "shadow"` in its details.
10. **`/api/questions/current` adds `state`** (the slot's status) and answers `body: null` whenever the slot is not `pending` (already posted, skipped, taken down) or the mode is `off`, so the owner-side task never posts a duplicate. The page's index uses `state` too (the mock reads a top-level `status` as an HTTP code).
11. **Take it down** marks the slot `taken_down`: the loop does not re-post that week by itself; Post now still can.
12. **Reorder** is Up/Down buttons (page and panel), not drag.
13. **Moved into the Posts page (2026-10-19, owner: *"where on the website is questions? can we put the question stuff in post"*).** Branch `questions-in-posts`. The page module became `site/public/assets/questions-section.js`, mounted by `page-posts.js` after Sticky messages (the sticky-desk pattern); `posts.html#sect-questions` opens it (`posts-hash.js:SECTION_HASHES`). The nav entry is gone; `questions.html` is a redirect to the section. History, Settings and Logs are foldouts inside the one section instead of their own sections. `FEATURE_PAGES["question"]` is `posts.html#sect-questions`, so the guides and log links follow. The `question_warn_template` DEFAULT now says *"Add some under Weekly questions on the Posts page or with /questions."* (a saved override is untouched). `/questions` and every API route are unchanged.
14. **This week, Undo skip and Post one now (2026-10-19, branch `questions-this-week`).** Measured live by the conductor: after the 09:00 slot resolved `skipped_empty`, the page, panel and `/api/questions/current` kept showing that passed slot for the 24-hour catch-up, and Skip → Undo skip re-opened it as `pending`, so the next tick posted the first queued question at once. Now:
    - **This week** is the passed slot ONLY while it is still `pending` (inside the grace, or catching up after downtime). Once settled in any way it is the next slot. `/api/questions/current` follows (body only while the shown slot is `pending`), so the owner-side task is never handed a settled week's question.
    - **Undo skip never re-opens a passed slot.** It acts only on a future skipped slot; a passed skipped week answers *"That week's time has passed, so it stays skipped. Post one now puts a question up out of cycle."* (`slot_passed`). A passed `taken_down` slot stays settled too.
    - **Post one now** (owner, verbatim: *"make sure we have an override since this week we're gonna run an out of cycle question since we're late"*). The slot-bound Post now is FOLDED into it, one button on the section and the panel: if This week is a passed slot still `pending`, the post settles that slot (as before, `question.posted_by_bot`); otherwise it is an EXTRA — the top queued question goes up now, the question row is `posted` / `posted_by=bot` / `slot_at` NULL, no slot row changes, `question.posted_extra` (IMPORTANT) is logged, and the next scheduled slot takes the following question. Same mode (off refuses in words), template, thread setting and send path as the scheduled post; confirm first. History says *posted by Black Bloc · out of cycle*; Take it down works on it (site History, and the panel offers it on the latest extra) and puts it back at the top of the queue without touching any slot.
    - **Why folded:** once This week points at the upcoming slot, a slot-bound "Post now" would mean "post next week's early and leave next week empty", which two buttons side by side ("Post now" / "Post one now") could not make clear. The extra covers the real need (late this week); posting next week's early is Post one now + Skip this week.
    - **The Posts page keeps its scroll** across the section's redraws after every write (add, edit, remove, move, skip, post, take down, settings), and the `#sect-questions` jump happens on the first draw only.

## Follow-up 2026-10-19 — Post to test

Branch `post-to-test-more` (off `main` `0075473f`), slice 1 of the switch audit's P1
([`switch-audit-2026-10-19.md`](switch-audit-2026-10-19.md) §4). Owner: *"what we need is like post, just a test button to send to the post test channel"*.

- **What it does.** **Post to test** sends one copy of the question *This week* shows — the question the shown slot was posted with, otherwise the top of the queue — to the rehearsal home (`question_shadow_channel_id`, blank meaning `shadow_channel_id`, then the guard's channel, then the log channel: `shadow.channel_id(feature="question")`). The copy is `question_template` filled, exactly what Post one now would send, with no ping.
- **What it never touches.** No slot row (it reads `questions_moves.week`, which never writes), no queue order, no `status` / `posted_by` / `channel_id` / `message_id` on any question. It is not tracked: every press sends a new copy and the bot never takes one down.
- **Log row.** `question.rehearsed` (ROUTINE; `web.question.rehearsed` from the site) with the actor, `question_id`, `question`, `shadow_home`, `message_id` and `url` (the message link).
- **Refusals, in words.** Mode `off` (`questions_off`), nothing queued and nothing posted this week (`queue_empty`), no rehearsal home (`no_shadow_channel`, the existing `NO_REHEARSAL` sentence), test mode (`test_mode`), the home gone (`channel_gone`), Discord refusing (`not_posted`).
- **Doors.** `/questions` panel: a **Post to test** button on row 2, drawn only when the mode is not off, there is a question and a home resolves; with no home the panel says so in one line (`NO_HOME_LINE`). Posts page ▸ Weekly questions ▸ This week: the same button (quiet), the same one-line state when no home. `POST /api/questions/rehearse`; `GET /api/questions` gains `test_id` and `test_home`.
- **One sender.** The copy goes through `black_bloc/rehearsal_copy.py` (`reach`, `deliver`), the helper `posts.rehearse_post` now uses too.

### Deviations

1. **Shown in `shadow` as well as `on`.** The posts Post to test hides in shadow because Post it already goes to the test channel; here Post one now in shadow still consumes the queue, so a copy that touches nothing is still worth having.
2. **No rehearsal note.** The audit's P1 text says the copy carries the note; this same build retires `rehearsal_note` (owner sheet item p4h), so no copy carries one.
3. **Not tracked, never taken down** — no column was added (no schema change). The posts Post to test copy is tracked on `shadow_message_id` and taken down by the next Post it; a question copy stays in the test channel.
4. **The answer on the site names the channel** (`#post-test`) through `names.site_words`; the other `/api/questions` answers still carry Discord markup, unchanged.
5. **Panel words are code constants** (`questions_rehearse.LABEL`, `TESTED`, …), the existing `questions.py` convention for panel labels and answers; the posted words (`question_template`) are the key they always were.

## Follow-up 2026-10-19 — the Posts page's one switch (branch `posts-one-switch`, NOT merged)

Owner sheet items p1a, p1d, p1e, p1f, i1, i2, p3a, p4f, p4i, p4j; the whole build is [`posts-one-switch-design.md`](posts-one-switch-design.md).

- `question_mode` and `question_shadow_channel_id` are **retired**; the question's mode is `posts_mode` (off: nothing posted, nothing checked; on: posted in `question_channel_id`).
- Post to test reads `posts_shadow_channel_id` (blank → `shadow_channel_id`).
- The section's settings fold no longer shows a mode.

Deviations: (1) with no shadow, `questions_moves.target_id` refuses in words while off instead of resolving a rehearsal home; (2) the warning DM's skipped reason reads `off` (was `shadow`).
