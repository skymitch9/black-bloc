# Co-streaming — one announcement naming both platforms, Twitch first, edited in place as platforms come and go

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 🔨 **BUILT on branch `costream`, 2026-09-20 — not merged, not
> deployed, nothing has met Discord.** The `## Deviations` foot is the truth where this body departs
> from what shipped, and `## What was NOT verified` is the honest half; sweeps `CS-a` … `CS-f` in
> `../access/sweeps.md` are the proof that is missing. Was: 📐 DESIGN, dispatched to Opus
> 2026-09-20 16:2x as branch `costream`. **Last verified: 2026-09-20 16:1x** against `main` `5afd58c`
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

*(written by the build agent, branch `costream`, **2026-09-20**, off `main` `64ccfbc`. Every item is
a departure from the body above; where the body is silent and a choice had to be made, it says so.)*

1. **`{url}` is filled BARE, and that was MEASURED, not assumed** (§B asks for exactly this). `render`
   (`golive.py`) fills `{url}` with `info.url or ""` and has never wrapped it, in embed mode or out
   of it — `golive_embed` changes the CARD, never the content string. `costream_render` fills the
   Twitch side the same way, so the Twitch preview is untouched; `{also_url}` is wrapped by
   `suppressed()` inside the fill. `test_an_owner_cannot_unsuppress_the_second_link_by_rewriting_the_template`
   is the guard: a template of `{also_url}` alone still renders `<…>`.
2. **`render` was refactored, not duplicated.** §B says the two keys fill "the way `render` fills
   `golive_template` today", which is a promise that only a shared implementation can keep. `render`
   now builds its mapping with `live_fields()` and fills it with `_filled()` (try → warn → default
   template); `costream_render` and `again_render` use the same two. Behaviour of `render` itself is
   unchanged — same output, same fall-back, same missing-placeholder tolerance.
3. **`again_render` was added, and it is the no-second-ping guard.** §A says `add_platform` must not
   ping. The body does not say what happens to the mention the announcement already carries. Building
   the new content with `render` would have re-prepended `ping_prefix(ping_role_id, fan_role_id)` —
   text Discord does not re-ping on an edit, but which could have differed from what is on the message
   if the keys changed mid-stream. `again_render` prepends `mention_prefix(message.content)` instead,
   so an edit can only ever keep the mention that is already there. `drop_platform`'s re-render uses
   it too.
4. **The co-stream card is KEPT and restyled when the order does not change, and REBUILT only when
   Twitch arrives second.** §B says the embed is the Twitch card. When Twitch was already the primary,
   rebuilding from the session row would have thrown away the box art and thumbnail, which the row does
   not store — so the existing embed is copied and its author, colour, url and footer are replaced.
   When Twitch arrives SECOND it must take the lead and the incoming `StreamInfo` is the only place its
   title, game and art exist, so the card is rebuilt from `announcement_embed`. A message with no embed
   is left with none, exactly as `_ended_embed` does.
5. **Promotion keeps `game` and `title`.** §A says promotion copies `also_*` into `source`/`url`/
   `platform`; it does not say what happens to the game. They are LEFT — a co-stream is one person
   streaming one thing to two places, so the reported game is still right, and blanking it would turn
   *"streaming **Celeste**"* into *"streaming **something**"* at the moment one platform stopped. This
   is also why no `also_game` / `also_title` columns were added.
6. **A fourth column, `also_started_at`, is in §A's parenthesis and was built.** Schema **45 → 46**,
   four nullable `TEXT` columns through `ADDED_COLUMNS` only.
7. **`open_session_on()` is a new query, because `open_session_for(..., source)` cannot find a
   co-stream by its second platform.** §A says every end path must check both sides; this is how.
   `source = ? OR also_source = ?`. For a row with no `also_source` it returns exactly what
   `open_session_for` returns, so single-platform behaviour is untouched. `poll_once`'s "is the Twitch
   session still there" check moved to it for the same reason.
8. **`_still_live` was split into `_side_live(guild, row, source, url, platform)` rather than
   duplicated**, with `platform=None` meaning "any streaming presence counts". `_still_live` passes
   `None`, so single-platform reconcile behaviour is byte-for-byte today's; a co-stream passes each
   side's platform, so a presence that says YouTube cannot vouch for the Twitch half.
9. **`poll_once` still short-circuits on an open session** — it calls `_go_live` when there is none
   **or** when `joins_session` says Twitch would join the one there is. Calling it unconditionally was
   simpler and would have re-run `_note_streaming` (a `pings.saw_streaming` upsert) once a minute for
   the length of every stream.
10. **`add_platform` takes the per-member lock and re-reads the session inside it; `_add_platform_once`
    is the inner half `_go_live_once` calls** (it is already holding that lock — taking it twice would
    deadlock). Checklist 6 and 37: the read and the decision are on the same side of the lock.
11. **The YouTube cog's `_go_live` and new `_add_platform` share `_hand_off(guild, member, info, door)`**,
    so the missing-cog warning and the `youtube.live_announce_failed` row exist once rather than twice.
12. **The validator is ONE function for BOTH wordings** (`checked_costream`), with the seven-placeholder
    set as `GOLIVE_COSTREAM_FIELDS`. §B asks the two keys to "behave alike"; a second validator would
    have been a second answer to the same question. ⚠️ **Consequence worth naming: `{duration}` is
    REFUSED here** although `golive_end_template` accepts it — nothing fills it on this path.
13. **Two files outside the brief's `site/` allowance had to change, and one of them is a gate failure
    if it does not.** `site/public/assets/labels.js` gains three label lines — without them
    `tests/test_settings_store.py::test_every_registry_key_the_site_shows_has_a_label` fails by name
    (the same deviation `golive-end-design.md` ▸ 9 recorded). `site/mock/server.mjs` gains the three
    `SETTING_SPECS` rows beside the contract row it was already getting, because the standing owner rule
    (2026-09-17) is registry + mock row + label for every word the bot posts, and the mock settings page
    is where the owner would look for them. Nothing under `site/public/assets/page-*.js` was touched and
    `C:/lcw/bb-golive-page` was not entered.
14. **The mock's session row also gained `platform`**, which the real route has returned since v84 and
    the mock did not. The three new fields would otherwise have rendered *"undefined and YouTube"* on the
    mock's own page. Seed row 12 is now a co-stream (Twitch + YouTube) and row 11 is explicitly
    single-platform, so the page being rebuilt in the `golive-page` worktree has one of each to draw.
15. **The validator's tests live in `tests/test_settings_store.py`, not `tests/test_golive.py`.** §D asks
    for "the validator" in the pure-render file; the validator is in `settings_store.py` and the owner's
    tests-mirror-the-package rule wins. Everything else in §D is where §D says.
16. **Three existing YouTube tests now say `golive_costream_mode` off out loud.** The hold-back they were
    written for is now what the OFF switch does, so they set it rather than being deleted — which keeps
    v135's behaviour under test by name (`test_a_stream_read_live_while_their_twitch_session_is_open_leaves_a_row_saying_so`,
    `test_that_row_is_written_once_per_stream_and_not_once_per_probe`,
    `test_the_row_shadows_with_the_live_half_exactly_as_the_announcing_one_does`). Two new tests cover the
    join and the missing-cog path.
17. **Four commits, not the six the brief sketched, and the reason is the AST guard.**
    `tests/test_logkinds.py::test_no_classification_entry_is_dead` refuses a classified kind that nothing
    emits, and `test_every_dynamic_kind_is_enumerated` wants a string literal at the `log_action` call —
    so `logkinds.py` had to land in the same commit as the cog that writes the two kinds, not with the
    storage and keys. `site/mock/server.mjs` carries both the settings rows and the sessions row, so it
    landed whole with the API commit rather than being split across two.
18. **NOT done, deliberately:** nothing merged, nothing deployed, nothing pushed to `main`; no key
    flipped (`golive_costream_mode` ships **on** as its registry DEFAULT — no guild row was written);
    `TODO.md`, `DONE.md`, `deploys.log` and `KNOWN_ISSUES.md` untouched; no `/golive` panel control was
    added for the three keys (§B does not ask for one, and the panel's **stream end** line has no
    co-streaming equivalent to name); the ended wording still uses the surviving platform only, as §B
    says, so *"was streaming on Twitch and YouTube"* is a later placeholder on an existing key.

## What was NOT verified

⚠️ **Nothing in this build has met Discord.** No announcement was posted, no message was edited, no
co-stream happened. Everything below is the suite's word, against `FakeChannel` / `FakeMessage` /
`FakeHelix` / a fake YouTube cog — the sweep rows `CS-a` … `CS-f` in `../access/sweeps.md` are the proof
that does not exist yet, and they can only be run by a person who is actually live on two platforms.

Specifically NOT verified:

- **That Discord suppresses the second preview.** `<https://…>` is library knowledge and the test proves
  the CHARACTERS, not the rendering. `CS-a` is the row that turns that into a fact.
- **That an edit does not re-ping.** The build proves no mention is ADDED and that `allowed_mentions`
  still names only the configured roles; that Discord does not notify on an edit is library knowledge.
- **The migration on a real database.** Schema 46 was applied by `Database.connect` in the suite's
  `tmp_path` databases only; the Fly volume's `golive_sessions` has never seen it. ⚠️ It is additive
  columns through `ADDED_COLUMNS`, so migrate-before-deploy is automatic — but that is an argument, not
  a measurement.
- **Any browser.** The Go-live page was not opened; the three new session fields were checked through
  the API and the mock, never rendered. The mock settings page was not opened either, so the three new
  keys have not been seen in a Settings card.
- **The YouTube half against a real channel.** The seam is exercised with the bot-check fixture and a
  fake client; the wall itself is still unreachable from here (`youtube-live-design.md` ▸ 23, 26).
- **A co-stream that starts on both platforms within one poll tick.** The lock and the unique index make
  one session the only possible outcome, and the tests drive the two arrivals in sequence; nothing here
  raced them.
