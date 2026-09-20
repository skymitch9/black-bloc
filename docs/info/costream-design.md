# Co-streaming — one announcement naming both platforms, Twitch first, edited in place as platforms come and go

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN, dispatched to Opus
> 2026-09-20 16:2x as branch `costream`.** **Last verified: 2026-09-20 16:1x** against `main` `5afd58c`
> (v141 live): `storage/db.py` `golive_sessions` (`:134–150` — ⚠️ the partial unique index
> `golive_open_session` already allows ONE open session per member, which is exactly the shape a co-stream
> needs), `ADDED_COLUMNS` (`:849`), `black_bloc/golive.py` (`StreamInfo` `:59`, `render` `:394`,
> `announcement_embed` `:209`, `ended_render` `:309`, `author_line` `:194`, `embed_footer` `:204`),
> `cogs/content/golive.py` (`_go_live_once` `:704`, `_end_live` `:778`, `_mark_ended` `:797`,
> `reconcile_open_sessions` `:596`, `_still_live` `:604`, `_still_live_on_youtube` `:626`, `set_announced`
> `:329`), `cogs/content/youtube.py` `_live_now` (`:526–540` — the v135 hold-back this design replaces).
> ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-20 16:1x)

*"also for when someone is co streaming I would like the message to say this person is streaming on twitch
and youtube, have the twitch stream first and only link preview the twitch stream. if someone is streaming
on one and adds the other i want to edit the previous message to reflect both are live. It would be silly
to suppress one of the live avenues someone is on"*

**What happens today (v135):** a member live on Twitch who also goes live on YouTube gets a
`youtube.live_seen` row with `announced: false, because: open_session:twitch` and nothing else — the
second avenue is suppressed. The reverse (YouTube first, then Twitch) is refused by the open-session check
in `_go_live_once`. Both are the thing the owner calls silly.

## A. The model — one session, two platforms

A go-live session stays **one row** (the unique index already says so). It gains three nullable columns
through `ADDED_COLUMNS`, schema **45 → 46**: `also_source TEXT`, `also_url TEXT`, `also_platform TEXT`
(plus `also_started_at TEXT` for the log line). `source` / `url` / `platform` keep recording whichever
platform came FIRST — that is history and the audit trail. **Rendering orders by platform, never by
arrival:** if either side is Twitch, Twitch is written first and is the only URL Discord may preview.

Three moves, all on the go-live cog so the youtube cog never renders anything:

| Move | When | What it does |
|---|---|---|
| **`add_platform(member, info, source)`** | a member with an OPEN session goes live on the other platform — from `youtube._live_now`'s open-session branch (replacing the hold-back) and from `_go_live_once`'s open-session check (the reverse) | writes `also_*`, re-renders the announcement as a co-stream, **edits** the message `announced_message_id` points at (whatever mode wrote it; a session with no message id records the platform and edits nothing), logs `golive.costream_added` (IMPORTANT — it changed a member-facing post). ⚠️ **No new announcement, no cooldown check, no ping**: it is an edit, like the ended edit |
| **`drop_platform(session, source)`** | one platform ends while the other is still live | if the `also` side ended: clear `also_*`, re-render single-platform, edit; if the PRIMARY ended: **promote** — copy `also_*` into `source`/`url`/`platform`, clear `also_*`, re-render, edit; the session stays open either way. Logs `golive.costream_dropped` (routine) with which side and whether it promoted |
| the existing end | the LAST live platform ends | today's `_end_live` / `_mark_ended` path, unchanged: `ended_at`, the ended template, the past-tense edit |

`_still_live` / `_still_live_on_youtube` (the reconcile) and every end path must check BOTH sides: a
session is over only when neither platform is live; one side ending is `drop_platform`, not the end.

## B. Rendering

- **Keys (every posted word is a key; all under `golive`):** `golive_costream_mode` (enum off / **on**;
  off = today's hold-back, so the owner can turn the behaviour off both ways), `golive_costream_template`
  (text, default *"**{name}** is streaming on **{platform}** and **{also_platform}**! Watch on {platform}:
  {url} · also live on {also_platform}: {also_url}"*), `golive_costream_author` (text, the card's top line,
  default *"{name} is live on {platform} and {also_platform}"*). Placeholders: `{name} {game} {title} {url}
  {platform} {also_url} {also_platform}` — filled the way `render` fills `golive_template` today (`format_map` over the
  tolerant `_Fields` mapping, `golive.py:394`, with the same fall-back to the default on a bad template), so the
  two keys behave alike; a validator refuses an unknown `{…}` at set time (the `events_moved_line` validator is
  the pattern).
- ⚠️ **Only the Twitch link previews.** The fill wraps `{also_url}` in `<…>` ITSELF (Discord's suppression
  syntax), so no wording edit can un-suppress it; `{url}` is filled exactly as `golive_template` fills it
  today — measure whether today's embed-mode content wraps `{url}` and keep that behaviour, do not guess.
  In embed mode the embed is the **Twitch** card (title, game, thumbnail from the Twitch `StreamInfo`), the
  author line is `golive_costream_author`, the footer reads *Black Bloc · via Twitch + YouTube*, the colour
  is Twitch's; the YouTube link lives in the content text, wrapped.
- **Single-platform renders are untouched** — `golive_template`, `golive_end_*`, the ended edit, all as
  today. After `drop_platform` the message is re-rendered with the single template for whichever side
  remains (so if Twitch ends and YouTube continues, the message becomes a YouTube announcement with
  YouTube's preview — the only live avenue is never suppressed).
- **The ended message** uses the session's primary at the moment the last platform ends (post-promotion);
  the fact it was a co-stream is in the log rows. If the owner wants *"was streaming on Twitch and
  YouTube"* in the ended wording later, that is one placeholder on the existing key, not this build.

## C. The seams

- `youtube.py:_live_now`, the open-session branch: with `golive_costream_mode` on, call
  `add_platform` (confirmed title / thumbnail / the searched id as today); the `youtube.live_seen` row is
  still written, `announced: true, because: "joined_session"`. With the mode off, today's row and hold-back.
- `golive.py:_go_live_once`, the open-session check: with the mode on and the open session's platform
  DIFFERENT from the incoming one, `add_platform`; same platform → today's behaviour (a duplicate).
- `/api/golive/sessions` rows gain `also_source`, `also_url`, `also_platform` (nullable) — ONE additive
  `contract.json` row + the mock. ⚠️ **The go-live PAGE is being rebuilt in a parallel worktree
  (`golive-page`) and its join already expects these three fields as optional** — do not touch `site/`
  beyond the contract row and the mock, and do not touch `C:/lcw/bb-golive-page`.
- Log kinds: `golive.costream_added` (IMPORTANT), `golive.costream_dropped` (routine), in `logkinds.py`
  with `HEADS` under golive; `youtube.live_seen`'s `because` gains the value `joined_session` (a detail,
  not a kind).

## D. Tests (mirror the package), and the gate

`tests/test_golive.py`: the co-stream render (Twitch first whichever came first; `{also_url}` wrapped;
the author line; the footer; embed mode is the Twitch card; the validator). `tests/cogs/content/test_golive.py`:
Twitch then YouTube → one session, `also_*` set, ONE edit of the announced message, no second announce, no
ping, `golive.costream_added`; YouTube then Twitch → same session, re-rendered Twitch first; the `also` side
ends → single render + edit + `costream_dropped`; the PRIMARY ends with `also` live → promotion, session
still open; the last ends → today's ended path; mode off → today's hold-back; a session with no message id
→ recorded, nothing edited; the reconcile treats one dead side as a drop, not an end.
`tests/cogs/content/test_youtube.py`: the hand-off calls `add_platform` and writes `because: joined_session`.
`tests/storage/test_db.py`: schema 46. `tests/test_logkinds.py`, `tests/test_settings_store.py`,
`tests/api/test_contract.py`: the counts. Both `pytest -n 8` orders (`BB_REVERSE=1`), `ruff check .`, the
ES-module parse, `node site/mock/check.mjs`, `discordmd.test.mjs`, `labels.test.mjs`, `clipmd.test.mjs`, env
cleared (`gotchas.md`). ⚠️ KI-26 (ten sightings): a stalled pytest is killed by its own process tree only.

## E. Docs

`code-notes.md`; this doc's `## Deviations` (dated) + `## What was NOT verified`; `architecture.md` (schema
46, keys, the two kinds); `docs/info/README.md` row; `golive-end-design.md` and `youtube-live-design.md` each
gain one dated line pointing here (the hold-back of deviation 24 is superseded); `sweeps.md` rows `CS-a…`
(a: a linked member live on Twitch starts a YouTube stream → the announcement is EDITED to name both, Twitch
first, only the Twitch link previews; b: the reverse order gives the same message; c: the YouTube stream ends
→ the message returns to Twitch-only; d: the Twitch stream ends first → the message becomes YouTube-only and
the session stays open; e: both end → the past-tense edit as today; f: `golive_costream_mode` off → today's
hold-back). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`. ⚠️ **Migrate before deploy** —
schema 46 is additive columns through `ADDED_COLUMNS`, applied by `Database.connect` as every column before it.

## Deviations

*(the build agent writes here what it had to do differently, dated)*
