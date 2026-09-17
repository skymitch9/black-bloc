# Polls — a shadow mode, a channel per poll, pinned while open, #announcements by default

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatching to Opus as branch
> `polls-shadow`.** **Last verified: 2026-09-17 09:2x** against `main` `e6bd6ac`: `black_bloc/cogs/community/polls.py`
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
| Where a poll goes | `polls.channel_id` per row; the site's create form already has a **Where** `channelSelect` (blank = `poll_channel_id`); the Discord `/poll` draft has no channel pick — it uses `poll_channel_id` (a select on the settings sub-panel, ~3293) |
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
only when `poll_who_can_create` lets the actor create). The chosen id goes into `polls.channel_id` as the site's
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

*(the build agent writes here what it had to do differently, dated)*
