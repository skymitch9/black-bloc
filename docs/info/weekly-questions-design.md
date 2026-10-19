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
bot posting immediately), **Skip this week** (the next question stays queued; the slot is marked
skipped), and for a bot-posted question **Take it down** (deletes the bot's message, puts the
question back at the top of the queue). A question the owner's account posted is never deleted by
the bot.

## 6. Surfaces

- **`/questions`** — one staff command opening an ephemeral panel: next slot (Discord timestamp),
  next question, queued count, buttons Add (modal, multi-line), Queue… (select → edit / remove /
  move), Post now, Skip this week. Buttons render only when valid.
- **`site/public/questions.html`** — the queue (drag or up/down to reorder, inline edit, remove),
  a paste-many add box, the history (posted by you / by the bot, link to the message), and the
  feature's settings section. Under the community group of the nav. No explaining blurbs.
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
