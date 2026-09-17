# Polls — a shadow mode, a channel per poll, pinned while open, #announcements by default

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 🔨 **BUILT on branch `polls-shadow` (2026-09-17) — NOT merged, NOT
> deployed, nothing has met Discord. The `## Deviations` foot is the truth where it departs from the body.** **Last verified: 2026-09-17 09:2x** against `main` `e6bd6ac`: `black_bloc/cogs/community/polls.py`
> (`post_poll` ~1421, `_post_results` ~1334, the `poll_channel_id` select ~3293), `black_bloc/api/tools/polls.py`
> (`_refuse_outside_the_test_channel_id`, `POST /api/polls`), `site/public/assets/page-polls.js` (`channelSelect`,
> the **Where** column), the `poll_*` registry keys, the live values read off the dashboard. ⚠️ Secret NAMES only.

## Owner ask, verbatim (2026-09-17 09:0x, a prompt box on "where should polls post?")

*"Can we add a shadow mode? Maybe when a poll is to be made we have a drop down of what channel it should be posted
to? Also we should pin the poll for its duration. Also let's default to announcements but in shadow it always post to
logs channel with a message saying because it's in shadow mode."*

## What exists today (measured)

| Piece | Today |
|---|---|
| `poll_mode` | enum `off` \| `on`, live **on**. No shadow |
| Where a poll goes | `polls.channel_id` per row; the site's create form already has a **Where** `channelSelect` (blank = `poll_channel_id`); ~~the Discord `/poll` draft has no channel pick~~ ⚠️ **WRONG, corrected by the build 2026-09-17:** the draft HAS had a `DraftChannelSelect` on `PreviewView` since the polls-panel wave. What it lacked was the DEFAULT (it opened on whatever channel `/poll` was run in), the shown `default_values`, and the `poll_who_can_create` gate — see `## Deviations` 5. The settings sub-panel select (~3293) is unchanged |
| Under `TEST_MODE` | `post_poll` writes `poll.would_open` and posts **nothing**; `POST /api/polls` refuses a channel outside the test channel in words (`refuse_guarded`) |
| `poll_channel_id` | live `#blackbloc-logs`, default the test channel |
| Pinning | none. `poll_auto_thread` opens a discussion thread |
| Results | `_post_results` posts the results card into the poll's channel when it closes |

## A. Keys

| Key | Kind | Default | Help (registry voice) |
|---|---|---|---|
| `poll_mode` | enum | `on` (unchanged) | gains **`shadow`**: *"off, shadow (every poll is posted for real, but into the log channel with a line saying why, so staff can rehearse), or on (polls go where they are pointed)"* |
| `poll_pin` | bool | **true** | *"true pins a poll's message while it is open and unpins it when it closes"* |
| `poll_channel_id` | (exists) | **#announcements** — ⚠️ the registry default stays the constant it has; the OWNER's default is the live value, which the conductor sets to `#announcements` (`1285381774876344340`) after the deploy | unchanged help |
| `poll_shadow_note` | text | `Posted here because polls are in **shadow** — it would have gone to {channel}.` | *"the line above a poll posted in shadow; {channel} is where it would have gone"* |

## B. Shadow — the posts feature's shape, not the go-live one

- With `poll_mode = shadow`, `post_poll` posts the REAL poll (panel or native, threads and all) into the shadow home:
  the guard's test channel while `TEST_MODE` is on, else `log_channel_id`. One home, `black_bloc/polls.py`
  `shadow_channel_id(bot, guild)` — mirror `posts.shadow_channel_id`, do not copy it: if a shared helper falls out,
  put it in `black_bloc/shadow.py` and have both call it. The content line becomes `poll_shadow_note` + the usual
  `open_text`, the row keeps its intended `channel_id` (so the card, the site's **Where** column and the results say
  where it WOULD go) and gains `shadow_message_id` (⚠️ a **migration**: schema 39 → 40, `polls.shadow_message_id
  INTEGER`; write `migrate_39_to_40` the way the earlier ones are written, test the upgrade on a 39 fixture). Votes,
  reminders, close and results work on the shadow message exactly as on a real one (they already key on
  `message_id` — store the shadow message there and the intended channel in `channel_id`; say in Deviations which of
  the two you chose and why).
- `poll.would_open` is written **only** when the intended channel is refused and the mode is `on` (today's line) —
  in shadow the log row is `poll.opened_shadow` with both channel ids.
- `POST /api/polls` and the Discord draft stop refusing a real channel while the mode is shadow: the poll is accepted
  and shadow-posted. With the mode `on` under `TEST_MODE`, today's refusal stays.
- Flipping shadow → on does not move open polls; the panel's staff block says how many open polls are shadow-posted.

## C. A channel per poll — the Discord draft catches up with the site

The `/poll` draft gains a **Where** select (`ChannelSelect`, text channels, default = `poll_channel_id`, one row,
only when `poll_who_can_create` lets the actor create). ⚠️ **Half of this already existed** — see the corrected
row in *What exists today* and `## Deviations` 5. The chosen id goes into `polls.channel_id` as the site's
form already does. The settings sub-panel's `poll_channel_id` select stays as the DEFAULT.

## D. Pinned while open

`post_poll` pins the message after posting (`message.pin(reason=...)`) when `poll_pin`; `_close`/`end_poll` unpins
before posting results; a `Forbidden` (no Manage Messages) is a warning log row `poll.pin_failed` and the poll still
opens. Shadow posts are pinned in the shadow channel the same way, so staff see the real thing. The pin system
message Discord adds is deleted when the bot can (it is noise), else left.

## E. Tests (mirror the package)

`tests/test_polls.py`: `shadow_channel_id`, the note text with `{channel}`; `tests/cogs/community/test_polls.py`:
shadow-post to the guard's channel with the note, `poll.opened_shadow` row, pin/unpin both key values, `pin_failed`
never raises, the draft's Where select present/absent by `poll_who_can_create`, votes on a shadow message count;
`tests/api/tools/test_polls.py`: create in shadow with a real channel is accepted; `tests/storage/test_db.py`: the
39 → 40 migration; `tests/test_settings_store.py`: the keys. Both `pytest -n auto` orders.

## F. Docs the build touches

`docs/info/code-notes.md`; the `poll-*` guide in `black_bloc/guides_seed.json` (a step for **Where** and a fact for
shadow); `docs/access/sweeps.md` rows `PS2-a…`; `docs/info/architecture.md` schema line (40); this doc's
`## Deviations`. NOT `TODO.md` / `DONE.md` / `deploys.log`.

## Deviations

> Written by the Opus build, 2026-09-17, branch `polls-shadow` off `main` at `905982b`. Where this
> foot and the body above disagree, **the foot is what was built.** Gate: `ruff check .` clean,
> `pytest -q -n 12` **6047 passed** forward and **6047 passed** under `BB_REVERSE=1` (5998 before),
> every `site/public/assets/*.js` parses as an ES module, `node site/mock/check.mjs` **ok — 19 pages,
> 175 routes, 14 core settings, all keys present**, `node site/mock/discordmd.test.mjs` ok.
> ⚠️ **Nothing here has met Discord**: no poll has been posted, no pin taken, no dropdown opened.

1. ⚠️ **The §B fork: the rehearsal's id goes in BOTH `message_id` and `shadow_message_id`.** §B
   offered two readings and asked which was taken. Taken: `message_id` carries the copy's id (so
   every existing reader — the gateway vote listener, `claim_reminder`, `close_poll`,
   `_write_results`, `repaint_panel`, `counts_for` — keeps working with no change at all), and
   `shadow_message_id` carries the same number as a MARKER meaning *"the copy this row has is a
   rehearsal, so it is not in `channel_id`"*. The alternative — `message_id` NULL, the id only in
   the new column — was rejected because **eleven** places read `row["message_id"]` as *"has this
   poll been posted?"*, and every one of them would have answered no for a poll that was visibly up.
   The cost of the choice is that `channel_id` alone no longer says where the message is, which is
   what `where_it_went` exists to answer.

2. **`where_it_went` / `hunting_grounds`, a pair, not one function.** Sending, guarding and the
   results want ONE channel; finding an existing copy wants ALL the channels a rehearsal could be
   in, because the cutover lifts the guard between the rehearsal and the real post. This is
   deviation 3 of the posts-shadow build met again, and it is solved the same way.

3. ⚠️ **`black_bloc/shadow.py` exists, but `posts.py` was NOT pointed at it.** §B said *"if a shared
   helper falls out, put it in `black_bloc/shadow.py` and have both call it"*. Only half landed:
   `posts.py` is owned by the `blackmail-threads` build running in the same tree and the brief
   forbade touching its files, so `posts.shadow_channel_id` / `shadow_channel_ids` are still their
   own copies. **The gap is guarded, not ignored:**
   `tests/test_shadow.py::test_posts_and_this_module_answer_the_same_question_the_same_way` asserts
   the two agree across three configurations, so a drift fails by name. **Follow-up for whoever
   merges second: make `posts.shadow_channel_id` a one-line delegation and delete that test's
   reason for existing.** One difference is deliberate — `shadow.channel_id` takes a guild OR a
   guild id, because `fetch_poll_message` has a row and no guild.

4. ⚠️ **There is no `migrate_39_to_40` function, because this repo has never written one.** §B said
   *"write `migrate_39_to_40` the way the earlier ones are written"*; the earlier ones are not
   functions. Every additive column since schema 1 is three edits in `storage/db.py` — the column in
   the `CREATE TABLE`, a row in the `ADDED_COLUMNS` table (`("polls", "shadow_message_id",
   "INTEGER")`), and `SCHEMA_VERSION` — applied by `Database._add_missing_columns` on connect. That
   is what was done, and it is what `posts.shadow_message_id` did at 37. The migration's test is
   `tests/storage/test_db.py::test_an_open_poll_gains_a_shadow_message_id_column_on_an_older_file`:
   it drops the column, stamps `schema_version` back to **39**, writes a poll with a real
   `channel_id` and `message_id`, reconnects, and asserts the column arrives NULL, the two old
   values are untouched and the stamp reads **40**.
   `::test_a_fresh_database_carries_the_shadow_message_id_column` covers the other door.

5. 🔴 **§C was already half-built, and the design's "What exists today" row is wrong.** It says *"the
   Discord `/poll` draft has no channel pick"*. It has had one since the polls-panel wave:
   `DraftChannelSelect`, a text-channel `ChannelSelect` on row 1 of `PreviewView`, writing
   `draft.channel_id`. What §C actually asked for that was MISSING, and what was built: the draft
   now opens on **`poll_channel_id`** (it opened on whatever channel `/poll` was run in), the select
   carries `default_values` so it SHOWS that channel rather than an empty placeholder, and it is
   rendered **only when `poll_who_can_create` lets the actor create**. Nothing else about the select
   changed.

6. **A cancelled poll is unpinned too, which §D did not ask for.** §D names `_close`/`end_poll`.
   A cancel also ends the poll's duration, and a pin nothing ever removes is the stranded-state
   failure checklist 3 exists for. `cancel_poll` calls the same `_unpin`.

7. **The unpin reads `message.pinned`, never `poll_pin`.** Checklist 3 again: a staffer who turns
   pinning off while a poll is running must not strand the pin that poll already took. The setting
   decides whether a pin is TAKEN; the message decides whether one comes off.

8. **`_post_results` unpins as its first statement, above the guard's early return.** The results
   card is legitimately not posted when the channel is gone or refused; the pin still has to come
   off. This is why the unpin is not beside the `channel.send`.

9. **`poll.unpinned` and `poll.unpin_failed` are two kinds the design did not name.** §D named
   `poll.pin_failed` only. Silence on the way back out would have made "the pin came off" and "the
   pin could not come off" indistinguishable, which is checklist 2. `poll.pinned` / `poll.unpinned`
   are ROUTINE beside `poll.opened`; the two `_failed` kinds are IMPORTANT for free by suffix.
   `poll.opened_shadow` is ROUTINE and had to be listed by hand — `logkinds.SHADOW` is the string
   `".would_"`, so the dry-run rule does not reach a kind that really posted.

10. **The failure reason for a rehearsal with nowhere to go is `no_shadow_channel`, on
    `poll.open_failed`.** The design did not name one. `no_channel` would have been a lie: the poll
    has a channel, it is the SHADOW home that is missing, and the two are fixed in different places.

11. **`_drop_pin_notice` matches on `reference.message_id`, not on recency.** Discord's `pins_add`
    system message names the message it is about. Deleting "the newest system message" would delete
    somebody else's pin notice in a busy channel. A failure is one `log.info` and the notice stays,
    which is what §D allows.

12. **`poll_mode`'s unknown-word fallback is `on`, not `off`.** `mode_of` reads an unrecognised
    value as `on` — the mode this key has shipped with since Phase 10 — rather than `off`. A typo
    that silently turned polls off would present as the feature being broken with nothing in the log
    to say why.

13. **`POLL_MODES` moved into `black_bloc/polls.py` as `MODES` and `settings_store` imports it.**
    Checklist 15: the mode helpers need the tuple and so does the registry, and two spellings of
    `("off", "shadow", "on")` is the shape that drifts. Consumers still say
    `from ...settings_store import POLL_MODES` and did not change.

14. **`site/public/assets/page-polls.js` needed no work beyond one sentence.** `modeSwitch` renders
    whatever `spec.choices` holds, so adding `shadow` to the registry gave the Polls page a
    three-way switch for free; only `SWITCH_HELP` was rewritten to say what the middle position
    does. The **Where** column already reads `channel_id`, which is exactly the "where it WOULD have
    gone" the design wants.

15. **`tests/api/conftest.py` gained `WebMessage.unpin`.** One additive method beside the existing
    `pin`. Without it every website end and cancel would have logged `poll.unpin_failed` and passed
    anyway — the silent-failure shape these kinds exist to prevent. It is the only file outside the
    polls feature this build touched that another build might also.

### What was NOT done, and why

- 🔴 **`poll_mode` was NOT flipped to `shadow` and `poll_channel_id` was NOT set to
  `#announcements`.** Both are the conductor's, after the deploy, per the brief and §A. The registry
  defaults are unchanged: `poll_mode` still defaults to `on` and `poll_channel_id` still defaults to
  the test channel under `TEST_MODE`. Sweeps `PS2-a` / `PS2-b` are those two moves.
- **Nothing has met Discord.** No poll was posted, no message pinned, no dropdown opened, no pin
  notice deleted. Everything above is the hermetic suite and the mock; `python -m black_bloc` was
  never started (a worktree holds no token).
- **The pin notice deletion is unproven against the real API.** The fake posts a `pins_add` message
  with a `reference`, which is what discord.py's models say Discord sends; whether the live gateway
  fills `reference` on that message type is a sweep row (`PS2-e`), not a test.
- **`ruff format --check` was not run** — it is known to fail repo-wide and is not a gate.
- **No `TODO.md`, `DONE.md` or `deploys.log` edit**, per the brief.
- **Nothing was merged, deployed or pushed to `main`.**
