# A rehearsal home per feature, and a marathon notice with the detail and the control staff need

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-25 17:0x Phoenix),
> dispatched to Opus as branch `shadow-home-per-feature`** off `main` `0374f5a5` (v165 live; `marathon-ux` merged, not
> deployed — this rides with it as v166). **Last verified: 2026-09-25 17:0x** against that `main`: `black_bloc/shadow.py`
> — `REHEARSAL_KEY = "shadow_channel_id"` `:13`, `home_id(bot, guild)` `:36`, `channel_id(bot, guild, *, log_key)` `:41`
> (the rehearsal home, else the log channel), `channel_ids` `:55`, `channel_of` `:71`, `note_line(bot, guild,
> channel_words)` `:99`; the callers, by grep: `cogs/community/frontdoor.py` (`shadow.channel_id` ×2, `note_line` ×2),
> `cogs/moderation/modmail.py` (×1, ×2), `polls.py` (`channel_id`, `channel_ids`), `posts.py` (`shadow_home.channel_id(…,
> log_key=…)`), `minutes.py` / `minutes_session.py`, `cogs/community/birthdays.py` (×2 + note), `cogs/content/spotlight.py`
> (×2 + `channel_of` ×2 + note ×2), `cogs/content/marathon.py` (×2 + `channel_of` ×3 + note ×2), `preview.py` (note).
> Go-live's own shadow path lives in `cogs/content/golive.py` (check how it reads the home — the same key through its
> own name, or `shadow`). Live values (operator read 14:4x): `shadow_channel_id` = `#welcome-test`
> (1550284332365783091), `log_channel_id` = `#blackbloc-logs`, `frontdoor_mode` shadow aimed at `#welcome`,
> `marathon_mode` shadow. Settings namespaces: applications, automod, birthday, chat, core, cost, emoji, events, golive,
> guides, hide, honeypot, logs, marathon, memory, modmail, pings, poll, posts, raidtrain, request, rolemenu, tempvoice,
> voice, youtube. ⚠️ Secret NAMES only.

## The ask, verbatim (owner, 2026-09-25 17:0x Phoenix)

*"you posted the rehersal stuff in the welcome test, should have gone to lackblocl logs"* → offered (a) move every
rehearsal or (b) marathons only → *"for now make post go to welcome test, and everything else go to logs channel"*.

**Read as:** the front door's welcome POST keeps rehearsing in `#welcome-test` (it is aimed at `#welcome`, and seeing
it beside the real thing is the point); every other feature's rehearsal copies go to `#blackbloc-logs`. One global
home cannot say that, so every feature gets an OVERRIDE, blank meaning *the global one*.

## A. The model — one override key per feature that rehearses, read by the one helper

- `black_bloc/shadow.py` gains `feature: str | None = None` on `home_id`, `channel_id`, `channel_ids` and `note_line`
  (and `channel_of` if it needs the home to pick): with a feature, the helper reads **`<namespace>_shadow_channel_id`**
  first and falls back to `shadow_channel_id`; the note line names the real target as today. One place decides,
  never a caller.
- **The keys**, type `channel`, default blank, one per feature that rehearses (the callers above + go-live):
  `frontdoor_shadow_channel_id` (namespace: whatever the front door's keys use — `frontdoor_*` sits in `core`? check
  `namespace_of` and put it where `frontdoor_mode` lives), `posts_shadow_channel_id`, `golive_shadow_channel_id` (covers
  spotlight, which is golive's), `marathon_shadow_channel_id`, `poll_shadow_channel_id`, `birthday_shadow_channel_id`,
  `modmail_shadow_channel_id`, `tempvoice_shadow_channel_id`, `honeypot_shadow_channel_id`, `automod_shadow_channel_id`,
  `minutes` (namespace `voice`? put it beside `minutes_channel_id`). Help text on each: *Where this feature's rehearsal
  copies go while it is in shadow — blank means `shadow_channel_id`.* Registry + mock + labels + each feature's
  settings drawer on its page (`placeSettings` or the namespace drawer) + the KI-36 join fixture where the namespace has
  one. The global `shadow_channel_id`'s help gains one sentence: *A feature's own `…_shadow_channel_id` wins over this.*
- Every caller passes its feature word. `preview.py`'s note line gets the feature the preview is of, if it knows it,
  else none.
- ⚠️ **No live values are set by the build.** After the deploy the CONDUCTOR sets, through the site: `shadow_channel_id`
  → `#blackbloc-logs`, `frontdoor_shadow_channel_id` → `#welcome-test` — the owner's exact state. Say in Deviations
  that a guard-era `TEST_MODE` path (`guard.allows_channel`) is untouched.

## B. Doors

The Settings page (every key lands in its feature's drawer) and `/settings` (the channel keys are already settable
there — confirm the new ones appear in the picker's group). No new panel moves.

## C. Logging

Every existing `*.would_*` / `*_shadow` row gains `shadow_home` (the channel id actually used) so a reader can tell
which home a rehearsal went to. No new kinds.

## D. Tests, docs, gate

`tests/test_shadow.py` (the override wins, blank falls back, the note line unchanged, `channel_ids` includes the
override), one test per caller file asserting the feature word is passed (a rehearsal post lands in the override when
set — the fakes already capture channel ids), `tests/test_settings_store.py` (the keys, types, defaults, namespaces),
`tests/api/test_contract.py`, the key count guards, the join fixtures. Both `pytest -n 8` orders, `ruff`, ES parse,
node tests, `check.mjs` on a port of the builder's own. Docs: `code-notes.md`; this doc's foot; `architecture.md`
(the keys); `docs/info/README.md` (one row); `docs/info/cutover-plan.md` one dated line (the shadow home is per
feature now); `sweeps.md` rows `SH-a…` (a: set `frontdoor_shadow_channel_id` and `shadow_channel_id` as above → the
next front-door rehearsal lands in #welcome-test and the next marathon notice in #blackbloc-logs; b: blank the front
door's → it follows the global). NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`. No schema.

## E. The marathon notice — detail and control, not two buttons (owner, 17:0x: *"also pause it and remove it, thats not enough control over the schedule or enough detail"*)

The feed's *added* notice (and the next-event / suggestion notices, same shape) today is one sentence with **Pause it** /
**Remove it**. It becomes:

- **An embed** (the same construct the go-live card uses) titled with the marathon's name, and fields: **When** (the
  schedule's start – end as `<t:…:f>`, or *dates not published yet*), **Read from** (the source words + the schedule
  link), **Channel** (the channel row it airs on, as a link), **Schedule** (the reading line: *read 2 min ago · next in
  28 min · 11 runs · 3 BaF* or *not published yet — the tracker answers 404; read again in 30 min*), **Event** (the mode
  word: *No event* / *One event for the marathon* / *An event per BaF run* / *Both*, and *Event #N — approved* when one
  exists), **Found by** (the feed) — every label a constant, every value from the row (`marathon_feed_added_template`
  stays the text above the embed).
- **Row 1 — the decisions:** **Pause it** / **Remove it** (as today, persistent, staff-gated) and **Read it now**
  (re-read the schedule, then EDIT the notice's embed with the fresh reading — the one place the schedule's detail
  updates in Discord without the panel).
- **Row 2 — the event select:** a persistent `Select` *Event: none / marathon / runs / both* (`custom_id`
  `marathon:feed:<feed>:<ref>:mode`) that sets the marathon's `event_mode` (§A of the event-modes design, the same
  function the site uses) and edits the embed's Event field.
- **Row 3 — everything else:** **Manage…** opens the SAME marathon card `/event` ▸ Marathons… shows for that marathon,
  ephemeral to the presser (the run pick, Who is who, the channel, the interval, Refresh the board, the board's pin) —
  full control without a second copy of the moves — and **Open on the site** (a link button to `events.html#marathon-<id>`).
- After Remove it the embed stays with a struck title and the buttons are removed, as today. Every button and the
  select survive a restart (KI-20, the `DynamicItem` template the feeds build used).
- Tests: the notice's embed fields from a fixture row (published / unpublished / with an event); Read it now edits the
  embed; the select sets the mode and edits; Manage… opens the card for staff and refuses a member in words; the
  custom ids round-trip through `from_custom_id`. Sweeps `SH-c`: a feed-added notice in the rehearsal home shows the
  six fields and the three rows.

## Deviations

*(the build agent writes this)*

## What was NOT verified

*(the build agent writes this)*
