# The BaF point system — layer 1: engine, storage, API (and the specification layers 2 and 3 are built from)

> **Audience:** the conductor, reviewers, and the agents that build layers 2 and 3 from this page alone.
> **Status:** TRACKED · ✅ **LAYER 1 MERGED** to `main` (`4ab03a82`), schema **91 → 92**, keys 1091 → 1147, contract
> routes 346 → 360, log head `points` (filed under `core`), 10 kinds. 🔨 **LAYER 2 BUILT on branch `points-discord`**
> (off `main` `4ab03a82`), **NOT merged, NOT deployed**: no schema change; registry keys **1147 → 1176** (29 word
> keys, all `core`; `CORE_KEYS` 317 → 346); log kinds **+3** (`points.would_dm`, `points.dm_failed`,
> `points.announce_failed`); no new route (§G).
> **Last verified: 2026-10-09** (layer 2: the hermetic suite, `ruff`, `scripts/site-gate.ps1 -Port 8833` and the 14
> `site/mock/*.test.mjs` — figures under *Gate (layer 2)*; ⚠️ nothing of layer 2 has met Discord). Layer 1: by the
> hermetic test suite, `ruff`, `site/mock/check.mjs` against the branch's own
> mock on port 8823 (started by `scripts/site-gate.ps1 -Port 8823`) and every `site/mock/*.test.mjs` (figures under
> *Gate*). ⚠️ **NOT checked:** nothing here has met Discord (layer 1 has no Discord code); no browser rendered anything
> (there is no page); schema 92 has not run on the live database. Secret NAMES only (none here).
>
> **This REPLACES** the per-game time-board idea of the morning of 2026-10-09 (nine questions, five passed to staff —
> [`TODO.md`](../TODO.md) ▸ *Session 2026-10-09*). Owner, ~1:1x PM, after Pawpette's spec: *"Okay so we need to change
> up the design completely"*. The `/pb` feature's tables (`pb_matches`, `pb_runs`, `pb_posts`,
> [`pb-feed-design.md`](pb-feed-design.md) §G) stay as they are; `pb_feed_mode` stays `off`.

## The ask (verbatim)

From the `#blackbloc-logs` thread *Point System* written by [Stars Glitter] Pawpette, Fri 2026-10-09 ~1:10 PM:

- **For XP:** "5 xp for 1 min", "25 xp for 10 min", "50 xp for 15 min", "100 xp for 30 min"
- **For points:** "10 points per game"
- **Submission requirements:** "Player name", "Game", "Image/Video Link (must show livesplit or IGT from game for
  image)", "Time"
- **Columns:** "player", "total runs", "total exp/xp", "speedpoints"
- **System Display:** "Leaderboard - Top 10 if possible, if not Top 5"; "Announcement - when someone from Top 10 is
  deranked or if someone in Top 10 moves up"; "If people want to view the full board maybe a command?"; "If people
  want to know how many points to get to the next rank make that a command as well"
- **Bounty System:** "Bonus points for submitting a certain game/game of the month"

## The owner's eleven decisions (2026-10-09 ~2:3x–2:5x PM)

1. **XP tiers are FLOORS** by the run's length: ≥ 1 min → 5, ≥ 10 min → 25, ≥ 15 min → 50, ≥ 30 min → 100; *"5 is
   min 100 is max"* — a run under a minute still earns 5, nothing earns over 100. The tier table is a key
   (`points_xp_tiers`), as are the two bounds.
2. *"Each run is 10 points"* — 10 speedpoints per APPROVED run, every run (`points_per_run`).
3. *"Points but let's add a way to filter by xp"* — the board ranks by speedpoints; XP is a switch
   (`?by=xp`; `points_board_order` is what it opens on).
4. *"I think 4 is next person up in the leaderboard"* — *points to the next rank* = the gap to the NEXT PLACE up.
   ⚠️ To be confirmed by staff; the wording is a key (`points_next_rank_said`).
5. *"5 yes"* — staff approve every submission before it counts; a verifier role (`points_verifier_role_id`, blank;
   mentors later) may approve too; staff always can.
6. *"By game but have a note of the category too so people know what was run"* — a run is keyed by game; the
   category is free text shown with it.
7. *"No limit for now"* — repeat runs of a game all count.
8. *"Speed and pbs"* — top-places announcements go to `#speed-and-pbs` (`points_channel_id`, default
   `1076003845232148580`); ping role key blank (`points_ping_role_id`).
9. *"They'll happen during events we plan so we can add logic to link to it to an event / We can also set to à la
   carte games. Bonus will be determined as a multiplier or extra points, we need a drop down"* — a bounty is one or
   more games + a bonus kind (`multiplier` | `extra`) + an amount + a window that is EITHER an event (an `events` row;
   live while the event is) OR a start and an end date.
10. *"Forever for now"* — no seasons, no resets (§Not built).
11. Where it lives (*"That's good"*): `/pb` becomes the board panel (layer 2); a Leaderboard page with a bounties
    editor (layer 3). Still holding from the morning: proof (a video or image LINK) on every submission; speedrun.com
    and therun.gg are read-only sources for later link prefill (§Not built); the feature starts in **shadow**; every
    posted word is a key.

## The layer plan

| Layer | What | State |
|---|---|---|
| **L1** | Pure engine `black_bloc/points/`, storage (schema 92), the moves both doors call, the view, the API `/api/points`, 56 keys, 10 log kinds, contract + mock | 🔨 branch `points-engine` |
| **L2** | Discord: `/pb` takes over as the board panel; a run is a modmail ticket decided on its card; the top-places post; the DMs (§G) | 🔨 branch `points-discord` |
| **L3** | The site: a Leaderboard page with the bounties editor (§H) | not started |

## A. The engine (`black_bloc/points/`, pure — no database, no Discord)

| Module | Does |
|---|---|
| `model.py` | The states (`pending` `approved` `rejected` `removed`), bonus kinds, orders (`points` `xp`), change kinds (`entered` `left` `up` `down`), `PointsError(code, **fields)` |
| `clock.py` | `seconds_of` — a typed time to seconds or a refusal; `shown` — seconds the speedrun way |
| `xp.py` | `xp_for(seconds, tiers, low, high)`; `parse_tiers` / `tiers_text` (the key's text both ways); the shipped tiers |
| `bounty.py` | `Bounty`, `live_at`, `matches` (game names compared without capitals or extra spaces), `with_bonus`, `points_for` |
| `scoring.py` | `Rules` (tiers, low, high, per run) and `score(seconds, game, at, rules, bounties) → Score(xp, speedpoints, bounty_id)` |
| `board.py` | `Row` (a member's approved totals), `standings`, `next_rank`, `diff` |

### A1. A time as typed

`seconds_of` reads `1:23:45.67` (h:mm:ss), `23:45` (m:ss — minutes may pass 59 when there are no hours: `90:00` is
90 minutes), `45.2` / `45` (a plain number is seconds), and units in falling order — `1h 2m 3s`, `1h2m3s`, `2m`,
`90s`, `1 hour 5 minutes`. Refused: nothing typed (`no_time`); anything else (`bad_time`, with what was typed in the
words): seconds or minutes of 60+ after a larger unit, units out of order or twice, zero, negatives, junk, over
100 hours. `shown` writes back `1:23:45.67`, `23:45`, `0:45.20`, hundredths only when the run has them.

### A2. XP — floors, kept between the least and the most

Highest tier whose floor the run reaches, then `min(max(that, points_xp_min), points_xp_max)`.

| Run | 59 s | 60 s | 599 s | 600 s | 899 s | 900 s | 1799 s | 1800 s | 5 h |
|---|---|---|---|---|---|---|---|---|---|
| XP | 5 (the least) | 5 | 5 | 25 | 25 | 50 | 50 | 100 | 100 (the most) |

`points_xp_tiers` is text — `1:00=5, 10:00=25, 15:00=50, 30:00=100`, any time format §A1 reads, any order, 1–10 tiers,
each XP 0–100000; it is stored in one spelling, earliest first. A tier list the engine cannot read is refused at the
settings door (`checked_point_tiers`), and a stored one that somehow cannot be read falls back to the shipped tiers
with a log line.

### A3. Speedpoints and bounties

A run earns `points_per_run` (10). A bounty raises it while it is live for the run's game: `multiplier` →
`round(base × amount)` (half up), `extra` → `base + amount`. XP never changes with a bounty.

**Stacking (builder's call):** when several bounties are live for the game, the **single best** applies — the one that
gives the most speedpoints; on a tie, the OLDEST (lowest id). A bounty that would not raise the points is not named.
Worked: base 10, live `×2` (#1), `+15` (#2), `×1.5` (#3) → #2, 25. Base 20, same three → #1, 40.

**When a bounty is live** (`live_at`): active, and `starts_at ≤ at < ends_at`. **The clock `at`** is when staff
approved the run (`points_bounty_clock = approved`, the brief's wording) or, if staff switch it, when the member
submitted it (`submitted`). **An event bounty's window** is its event's scheduled window — `starts_at` to `ends_at`, or
`starts_at` + 120 minutes when the event has no end (`events.DEFAULT_DURATION_MINUTES`) — while the event's status is
`approved`, `live` or `done`; a `pending`, `denied` or `cancelled` event, or an event row that is gone, makes the
bounty never live. **Dated bounties:** an ISO date or date-time; one with no zone is read in the server's zone
(`default_timezone`, America/Phoenix), and a bare END date counts that whole day (`2026-10-31` ends at the start of
11-01).

### A4. The board

`standings(rows, by)`: members with at least one approved run, most speedpoints first; a tie goes to more XP, then
to whoever's LAST approval came first (they got there first), then the lower user id so the order is total. `by=xp`
swaps the first two. Places are 1, 2, 3 … with no shared places.

Worked (points): A 20 sp / 50 xp / last 13:00, B 20 / 100 / 14:00, C 20 / 50 / 12:00 → **B, C, A**.

### A5. The next place up

`next_rank(board, member)`: first place → `first` (nobody ahead); not on the board → `unranked`; otherwise `climb`
with the member above, and **gap = their points − mine + 1** — one more than the difference, so passing them never
depends on a tie-break — and `runs = ceil(gap / points_per_run)` (by speedpoints only). Worked: A 50, B 30, C 30
(later) → B needs 21 to pass A (about 3 runs at 10); C needs 1 to pass B.

### A6. What moved in the top N (the announcement)

`diff(before, after, top)` over everyone inside the top `points_top_n` before or after: **entered** (in the top now,
not before — from place 11, or new to the board), **left** (in before, not now — pushed to 11, or their only run
removed), **up** / **down** (inside both, place changed). Pawpette's *deranked* = `down` or `left`; *moves up* = `up`
or `entered`. Moves outside the top are never announced. Order: by the new place, the leavers last.

| Case | Before → after | Changes |
|---|---|---|
| A newcomer at #2 | 1 X 30, 2 Y 20 → 1 X 30, 2 Z 25, 3 Y 20 | Z entered #2, Y down 2→3 |
| A swap | X 30, Y 20 → Y 40, X 30 | Y up 2→1, X down 1→2 |
| Pushed out (top 2) | X, Y, Z → X, Z, Y | Z entered #2, Y left (was #2) |
| Fewer than 10 members | X → Y 40, X 30 | Y entered #1, X down 1→2 |
| No change | — | none |

A newcomer at #1 moves everyone below them down a place, and each gets a line; layer 2 posts them as ONE post.

## B. Storage (schema 92)

`black_bloc/storage/db.py` gains two tables (no column migration; `tests/storage/test_db.py::
test_a_schema_91_file_gains_the_point_tables_and_loses_nothing`). `black_bloc/points_store.py` is the only module that
reads or writes them.

- **`points_runs`** — `id`, `guild_id`, `user_id`, `game`, `category` (free text, nullable), `seconds` (REAL),
  `proof_url`, `submitted_at`, `state` (`pending` default · `approved` · `rejected` · `removed`), `decided_by`,
  `decided_at`, `reason`, `xp`, `speedpoints`, `bounty_id`, `note` (the member's own, nullable), `ticket_id`
  (nullable — the modmail ticket the run was submitted through, §G). Indexes `(guild_id, state, id)` and
  `(guild_id, user_id, state)`, and a partial UNIQUE `(guild_id, ticket_id) WHERE ticket_id IS NOT NULL` (one run per
  ticket). `xp`, `speedpoints` and `bounty_id` are written at
  approval and stay as they were unless staff edit the run or press Recompute.
- **`points_bounties`** — `id`, `guild_id`, `name`, `games` (JSON list), `kind`, `amount` (REAL), `event_id`
  (nullable), `starts_at`, `ends_at` (nullable; both set when `event_id` is not), `created_by`, `created_at`, `active`.

The board is NOT stored: `points_store.totals` sums the approved runs per member every time
(`COUNT`, `SUM(xp)`, `SUM(speedpoints)`, `MAX(decided_at)`).

**Races (checklist 6):** every write runs under `points_moves.lock_for(bot, guild_id)` (one `asyncio.Lock` per server
— the board is one thing), and every state change is a conditional write (`update_run(…, when_state=…)`: `UPDATE …
WHERE id = ? AND state = ?`) that refuses in words if another process got there first
(`test_two_approvals_at_once_count_the_run_once`).

## C. The moves (`black_bloc/points_moves.py`) and the view (`black_bloc/points_view.py`)

The moves are the ONE implementation both doors call. Each takes `via` (default `VIA_DISCORD`), logs its row through
`kind_via` and returns an `Outcome` whose `value` is a `Result(id, dm, dm_to, announce, changes)` and whose
**`changed`** names what to re-render: `run:<id>`, plus `board` when the approved totals moved, plus `top` when the
top places moved; bounty moves answer `bounty:<id>`.

| Move | Who | Does |
|---|---|---|
| `submit(given)` | any member | `game` (1–100), `time` (§A1), `proof_url` (http(s) with a dotted host, ≤ 500) required; `category` (≤ 100) and `note` (≤ 300) optional → a `pending` run. Staff may pass `user_id` to submit for a member; a member naming someone else is refused (`not_staff`). A keyword-only `ticket_id=` records the modmail ticket the run came through — only layer 2's ticket flow passes it; the website route never does, and a `ticket_id` in a body is not read. |
| `approve(run)` (or `ticket_id=`) | staff or the verifier role | `pending` only → scores it (§A2, §A3) and writes `approved`. A verifier who is not staff cannot decide their own run (`own_run`); staff can. |
| `reject(run, reason)` (or `ticket_id=`) | staff or the verifier role | `pending` only → `rejected` with the reason. `Result.dm` = `points_dm_rejected`. |
| `remove(run, reason)` (or `ticket_id=`) | staff | `approved` only → `removed`; the board recomputes. `Result.dm` = `points_dm_removed`. |
| `edit(run, given)` | staff | the fields `submit` takes. **A `rejected` or `removed` run goes back to `pending`** (decision cleared) — the only way back, so *rejected → cannot be approved without a staff edit*; an `approved` run is rescored at its own clock; a `pending` run stays pending. |
| `recompute()` | staff | every approved run again under today's tiers, points and bounties, each at its own clock (staff changing a tier or adding a bounty for a past window is NOT retroactive until this). |
| `bounty_create(given)` / `bounty_edit(id, given)` / `bounty_end(id)` | staff | §A3's fields: `name` (1–100), `games` (1–25, each 1–100), `kind`, `amount` (multiplier above 1 and at most 10; extra a whole number 1–100000), and EITHER `event_id` (an event in this server) OR `starts_at` + `ends_at` (end after start); giving both is refused. An edit with `active: true` brings an ended bounty back (staff final say). |

Every refusal is an `Outcome(False, words, code, status)` — never a bare status. `points_mode = off` refuses every
move (`points_off`, 409); reads still answer. **In `shadow` everything works** — runs are taken, approved and
counted — and only the top-places post is a rehearsal (§G).

**After every move that changes the board** (`board_moved`): the before/after `diff` (§A6); if anything moved in the
top `points_top_n`, ONE row — `points.top_changed` in `on`, `points.would_announce` in `shadow` — carrying `top`,
`changes` and the rendered `lines`, and `Result.announce` carries the same lines for layer 2 to post.

**Words.** Member-facing and public words are keys (`said` → staff wording, falling back to the shipped words when a
staff edit cannot be filled — checklist 17). Staff-only lines are `STAFF_WORDS` constants (the brackets build's rule;
the verifier role sees them too, as a Tournament Organiser sees `TO_WORDS`). Names in words are display names through
`pb_feed.plain` (no markdown, no link), `<@id>` for someone who has left; games through `plain` too.

**The view:** `index` (the board's top N in the chosen order, `members`, `me` — the next place line, the live and
upcoming bounties, `pending` count for a verifier, every word key), `full_board`, `next_rank_of`, `bounties`,
`run_row`, `place_row`, `bounty_row` (with its one rendered `line`; dates in the server's zone as `Jan 31, 12:00`).

## D. Settings — 56 keys (layer 1) + 29 (layer 2), all under `core`

**Layer 2 added 29 word keys** to the same `POINTS_WORDS` block (1147 → 1176, `CORE_KEYS` 317 → 346): the panel's
footer and buttons (`points_panel_footer`, `points_points_label`, `points_xp_label`, `points_full_board_label`,
`points_next_rank_label`, `points_submit_label`, `points_feed_label`, `points_back_label`, `points_previous_label`,
`points_next_label`, `points_page_words`, `points_bounties_heading`), the form (`points_submit_title`,
`points_game_label`, `points_category_label`, `points_time_label`, `points_proof_label`, `points_note_label`,
`points_time_hint`, `points_proof_hint`), the run ticket (`points_ticket_subject`, `points_ticket_body`,
`points_close_refused_said`), the approval DM (`points_dm_approved`) and the five submission refusals that come from
modmail (`points_modmail_off_said`, `points_blocked_said`, `points_ticket_open_said`, `points_run_waiting_said`,
`points_cannot_open_said`). Labels in `labels.js`, rows in the mock, `contract.json` `core_keys`.

`points_` would be a 26th `/settings` group and the group select is at Discord's cap of 25 (the structure-backup,
pb-feed and brackets precedent), so every key is in `CORE_KEYS`; the brief's "a `points` namespace" is the `points_`
prefix and its own block in `settings_store.py`.

| Key | Type | Default |
|---|---|---|
| `points_mode` | enum off / shadow / on | **shadow** |
| `points_channel_id` | channel | `1076003845232148580` (#speed-and-pbs) |
| `points_shadow_channel_id` | channel | blank → `shadow_channel_id` |
| `points_ping_role_id` | role | blank (no ping) |
| `points_verifier_role_id` | role | blank (staff only) |
| `points_xp_tiers` | text, checked | `1:00=5, 10:00=25, 15:00=50, 30:00=100` |
| `points_xp_min` · `points_xp_max` | int 0–100000 · 1–100000 | 5 · 100 |
| `points_per_run` | int 0–100000 | 10 |
| `points_top_n` | int 1–25 | 10 (*"Top 10 if possible, if not Top 5"*) |
| `points_board_order` | enum points / xp | points |
| `points_bounty_clock` | enum approved / submitted | approved |

Plus **44 word keys** (`POINTS_WORDS`, each with its named fields checked on a staff edit): the post's title and four
lines (`points_announce_title`, `_entered`, `_left`, `_up`, `_down`), the board's two titles, four column names (Pawpette's
*player · total runs · total XP · speedpoints*), `points_board_line`, `points_board_empty`; the three next-rank lines;
`points_submitted_said` and every submission refusal (`no_game`, `too_long`, `no_time`, `bad_time`, `no_proof`,
`bad_proof`); `points_off_said`, `not_verifier` + `no_verifier_role_words`, `not_staff`, `own_run`, `no_run`,
`wrong_state` and the four `points_state_*` words; the DMs (`points_dm_rejected`, `_removed`, `_reason`,
`_no_reason`); the bounty line and its five parts (`multiplier_words`, `extra_words`, `until_words`, `event_words`,
`bounty_none`). Labels in `site/public/assets/labels.js`; mock rows in `site/mock/server.mjs` (`POINTS_KEYS`,
`POINTS_WORD_KEYS`, generated from the registry); `contract.json` `core_keys` 261 → 317.

## E. The API (`black_bloc/api/tools/points.py`, prefix `/api/points`)

Reads need a signed-in member (the read bucket). Submit spends the member write bucket (10 a minute). Approve and
reject need a signed-in member and spend the staff write bucket — the move decides (staff or verifier). Remove, edit,
recompute and the bounty writes are staff-only at the door (`writer_dependency`) and in the move. Every write passes
`via=VIA_WEBSITE` to the one move (checklist 34 — one write, one `web.points.*` row). Every refusal is
`{error, message}` with the move's status.

| Route | Answers |
|---|---|
| `GET /api/points?by=xp` | `{mode, by, orders, top_n, may_verify, staff, words, board[], members, me, bounties[], pending}` |
| `GET /api/points/board?by=xp` | `{by, rows[]}` — everyone |
| `GET /api/points/me` | the next place: `{kind, place, speedpoints, above_user_id, above_name, above_place, gap, runs, line}` |
| `GET /api/points/runs?state=&user_id=` | `{state, user_id, runs[]}` — a member gets their own (naming someone else is `not_verifier`, 403); a verifier any; the pending queue oldest first |
| `POST /api/points/runs` `{game, time, proof_url, category?, note?, user_id?}` | `{run, message, changed, announce}` |
| `POST …/runs/{id}/approve` · `/reject {reason?}` | same |
| `POST …/runs/{id}/remove {reason?}` · `PATCH …/runs/{id} {fields}` | same (staff) |
| `POST /api/points/recompute` | `{message, changed, announce}` (staff) |
| `GET /api/points/bounties` | `{bounties[]}` — every bounty, ended too |
| `POST /api/points/bounties` · `PATCH …/{id}` · `POST …/{id}/end` | `{bounty, message}` (staff) |

All 14 are in `site/mock/contract.json` (the real router answers them in `tests/api/test_contract.py` against
`seed_points`: a run in each state and a live bounty; the mock in `site/mock/server.mjs` against the same seed shape,
ids in `check.mjs`). Settings are read and written through `/api/settings` like every other core key.

## F. Log kinds — head `points`, filed under `core`

Each carries `via`; a run row carries `run`, `game`, the member as target. The `web.` twin via `kind_via`.

| Kind | Class | When |
|---|---|---|
| `points.submitted` | routine | a run came in (`seconds`, `proof_url`) |
| `points.approved` | routine (listed, so the `.approved` suffix does not make it loud) | `xp`, `speedpoints`, `bounty` |
| `points.rejected` | IMPORTANT | with the reason |
| `points.removed` | IMPORTANT (the `.removed` suffix) | with the reason and the run's `xp` / `speedpoints` |
| `points.edited` | IMPORTANT | `changed` fields, `was` (the state before), `reopened` |
| `points.recomputed` | IMPORTANT | `changed` / `total` — *beyond the brief's list: the recompute move needed a kind* |
| `points.bounty_set` | routine | create (`created: true`, the fields) or edit (`changed`) |
| `points.bounty_ended` | routine | — |
| `points.top_changed` | routine | the top places moved while `on` (`top`, `changes`, `lines`) |
| `points.would_announce` | shadow (routine by rule) | the same while `shadow` |
| `points.would_dm` | shadow (routine by rule) | layer 2: a decision DM not sent because `points_mode` is not `on` (`move`, `text`) |
| `points.dm_failed` | IMPORTANT (`_failed`) | layer 2: a decision DM Discord refused (`move`, `text`, `reason`); the move stands |
| `points.announce_failed` | IMPORTANT (`_failed`) | layer 2: a real top-places post that could not go (`channel_id`, `reason`, `lines`) |

## G. Layer 2 — Discord (built on `points-discord`, 2026-10-09)

The owner's decisions that shape it (2026-10-09): Q11 (*"That's good"*) — `/pb` opens the board, the speedrun.com
panel folds behind one button; Q1/Q5 — staff approve every run, the verifier role may too, never their own; **runs
are approved THROUGH MODMAIL** (*"Can the approvals go through modmail? The entry to use end user can be in /pb but
the staff just see it as a mod mail entry to be approved"*); Q12 (*"Silent"*) — opening a run ticket DMs nobody;
Q8 — the post goes to `points_channel_id`, the ping role blank = no ping, and shadow rehearses to the shadow home.

| Module | Does |
|---|---|
| `black_bloc/cogs/content/points.py` | The `Points` cog (in `bot.py:COGS`): `/pb` (moved here from the feed cog; same name, so `TOP_LEVEL` is unchanged), and the persistent Remove button |
| `black_bloc/points_panel.py` | The board panel and its surfaces: board, full board, pending list; the Submit form |
| `black_bloc/points_tickets.py` | A run as a modmail ticket: open it silently, Approve / Reject / Remove, the hold on Close, `settle` (the follow-through both doors run), `tell` (the DM) |
| `black_bloc/points_announce.py` | The one top-places post per move, routed by `points_mode` |

- **`/pb` — the board.** Hidden at `points_mode = off` (`HIDDEN_WHEN_OFF["points_mode"] = ("pb",)`; `pb_feed_mode`
  stays its own switch and moved to the settings panel's hand-added mode rows). The face: `points_board_title` /
  `_xp_title`, the top `points_top_n` as `points_board_line` rows (or `points_board_empty`), a **Bounties** field
  (`points_bounties_heading`) of the live bounties (or `points_bounty_none`). Buttons, each a key: the switch
  (`points_xp_label` / `points_points_label`), **Full board** (25 a page, `points_previous_label` /
  `points_next_label` / `points_page_words`, Back), **Next rank** (the member's next-place line drawn above the board),
  **Submit a run** (not while `off`), **speedrun.com…** (`points_feed_label`: the old feed panel, unchanged, with a
  Back to the board on its face — `pb_panel.home_of`), and for staff and the verifier role **Pending (N)** when N > 0: a
  LIST of the open run tickets whose run waits, each a link to its thread — not a second queue. Panel minutes reuse
  `pb_feed_panel_minutes` (the panel-minutes select is at Discord's 25 cap). Footer `points_panel_footer`.
- **Submit form** (`points_submit_title`): game, category, time (`points_time_hint`), proof link
  (`points_proof_hint`), note — five `Label`-wrapped inputs, labels and title clipped to 45, placeholders to 100. The
  fields are checked by the move's own checks BEFORE anything opens; then a modmail ticket of source **`points`** opens
  in the member's name (`modmail.open_a_ticket`), its subject `points_ticket_subject` and first message
  `points_ticket_body` (the fields as typed, blanks as —), then the proof link alone as a plain message so Discord
  previews it, then `submit(…, ticket_id=)`. **Silent:** no opening DM, and no `modmail.opened` row (the run's
  `points.submitted` carries `ticket` — one event, one row). One open ticket per member still holds (modmail's index):
  a member whose run waits is told `points_run_waiting_said`; one with another ticket open `points_ticket_open_said`
  (both write `modmail.open_refused`; the trade-off is [`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) **KI-44**);
  modmail off / blocked / no room: `points_modmail_off_said` / `points_blocked_said` / `points_cannot_open_said`.
- **The run ticket** is an ordinary ticket: the inbox's `A ticket…` select tags it `· run`, the header says *came in
  by a run submitted on /pb*, transcripts and logs are modmail's. Its card has Reply / Reply as Staff / Private note /
  Close… plus **Approve** and **Reject…** (no Send to… pair), and a **run** line (game, category, time, state, proof).
  The panel's copy of the card has the same moves. Approve/Reject are gated on staff OR the verifier role (the move
  gates again: `own_run`, `wrong_state`). **Close… is refused** in `points_close_refused_said` while the run waits —
  on the card, on the panel's copy, in the Close modal's submit, and on the site's close route (`run_pending`, 409).
- **Deciding (`points_tickets.settle`, both doors):** Approve/Reject call the move with `ticket_id=`; the decision line
  (the move's staff words, Reject adds the reason) is spoken into the ticket — with a persistent **Take it off the
  board…** button under an approval — and the ticket closes silently with that line as its reason. The member's DM:
  approve = the ticket-closed DM + `points_dm_approved`; reject = `points_dm_rejected`; remove = `points_dm_removed`.
  DMs go only while `points_mode = on`; otherwise `points.would_dm` with the words; a shut DM is `points.dm_failed`
  and the move stands. Then the top-places post. The site's approve / reject / remove / edit / recompute routes call
  the same `settle` (`via=website`), so a site rejection DMs and closes the ticket the same way.
- **Remove:** the button under an approved run's decision line (staff; a reason modal) → `remove` → the DM and the
  post. In channel mode the ticket's room is deleted at close, so there Remove is the site's (L3). Edit stays L3.
- **The top-places post (`points_announce.announce`):** one post (title `points_announce_title` + the lines) per move
  whose `Result.announce` is not empty. `on` → `points_channel_id`, `<@&points_ping_role_id>` above it when set,
  `allowed_mentions` = that role only. `shadow` → `shadow.channel_id(feature="points")` (`points_shadow_channel_id`,
  else the global shadow home) with the rehearsal note, no ping, nothing to the real channel. `off` → nothing. A real
  post that cannot go is `points.announce_failed` (IMPORTANT, never the dry run's kind).
- Every surface has a `render_again` (checklist 36); components use the shared `on_error` (checklist 30).

### L2 decisions (builder's calls beyond the brief)

1. **`/pb` lives in the points cog**, not the feed cog; the feed cog keeps its loop. `points_mode` hides `/pb`;
   `pb_feed_mode` moved to `settings_panel.EXTRA_MODES` so its mode line stays (the mode block is 25 lines).
2. **One open ticket per member still holds** — a second run waits for the first to be decided (refused in words).
   Changing that needs a schema change to modmail's open-ticket index and DM routing; not done. The owner chose to
   ship it so (2026-10-09); tracked as [`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) **KI-44**. Each such refusal is a
   `modmail.open_refused` row (`reason` `run_waiting` / `already_open`).
3. **The fields are checked before the ticket opens**; a move that still refuses after it opened closes the ticket
   silently.
4. **The proof link is posted again as a plain message** so Discord previews it (the relay is an embed).
5. **Decision DMs follow `points_mode`** (layer 1's §G: not sent in shadow/off, `points.would_dm`) — so in shadow a
   member who submitted is not DM'd the decision; staff can still Reply on the ticket. The staff answer says so.
6. **The approve DM is sent only when a ticket closed** (§Not built: *a DM on approval* otherwise).
7. **Remove lives under the decision line in the thread** (persistent button), so it exists in thread/forum modes
   only; channel mode deletes the room.
8. **Pending (N) counts open run tickets**, not every pending run (a site-submitted run has no ticket).
9. **Panel minutes reuse `pb_feed_panel_minutes`** (no new option on the 25-option select).
10. **The Close-refusal words are a key** (`points_close_refused_said`), as the brief listed; the Reject / Remove
    modal words, the Pending list and the run line are staff-only constants.
11. **The site's decide routes run `settle`** (close the ticket, DM, post) — no new route; the site's close route
    refuses a waiting run.
12. **`/pb`'s description** is now *"The speedrun leaderboard: the top places, your next rank, a run"* (a literal, as
    every command description is), and the chat persona's `/pb` line says what the board does.

## H. Layer 3 — the site (to build)

A **Leaderboard** page (`leaderboard.html`, `page-leaderboard.js` — the name the contract's `read_by` uses): the board
with the Points / XP switch and *Full board*, *My next place*, a Submit form, the Pending queue (verifier), run Edit /
Remove (staff), Recompute (staff) — ⚠️ the Pending queue is a VIEW of the open run tickets (`GET /api/points/runs?state=pending`, each row carrying its `ticket_id` and a link to the ticket), not a second queue: deciding happens on the modmail ticket (§G) — and the **bounties editor**: name, games (a list), the **bonus kind dropdown**
(multiplier / extra — the owner's *"we need a drop down"*), amount, and the window — an **event picker** (the events
list) OR start and end dates. The page's settings drawer carries the 12 operational keys; labels exist. Search and
filter chips through the one shared module in `ui.js`; channel pickers read `#name · Category`; no explaining blurbs.

## Decisions made by the build beyond the brief

1. **Keys under `core`** (§D) — the 25-group cap; the brackets / pb-feed precedent.
2. **The tie-break** (§A4): more XP, then the earlier LAST approval, then the user id — the brief named the first two.
3. **One bounty at a time, the best; the oldest on a tie**, and a bounty never touches XP (§A3).
4. **`points_bounty_clock`** — the brief said *"a run approved while a bounty … is live"*; that is the default, and the
   key lets staff judge by the submission instead (a late approval would otherwise lose an event's bonus).
5. **An event bounty uses the event's scheduled window** while it is approved / live / done; no end = +120 minutes.
6. **Next rank = one more than the gap**, with *about N runs*; first place and *not on the board* have their own lines.
7. **A member pushed down a place inside the top N gets a `down` line** — that is what *deranked* reads as.
8. **A verifier never decides their own run; staff may decide their own** (staff final say).
9. **Staff may submit for a member** (`user_id`); a member naming someone else is refused in words, not silently
   ignored.
10. **The way back from `rejected` or `removed` is a staff Edit**, which returns the run to `pending`; nothing is
    terminal.
11. **Recompute** is a staff move and a new kind (`points.recomputed`); settings and bounty changes are NOT
    retroactive until it is pressed.
12. **`points_board_order`** (the XP switch's starting side) and **`points_top_n` capped at 25** (an embed's field
    cap, and the brief's *Top 10 if possible*).
13. **A proof link must be http(s) with a dotted host**, ≤ 500 characters; no attachments (§Not built).
14. **A plain number is seconds**; times over 100 hours are refused.
15. **Bare bounty dates are in the server's zone, and an end date is inclusive.**
16. **Bounty amounts:** a multiplier above 1 and at most 10; extra a whole number 1–100000 (constants; staff-only).
17. **Importance:** rejected / edited / recomputed / removed are loud; approved is routine (§F).
18. **`brackets.access.holds_role` / `is_staff` are reused**, not copied (one implementation).
19. **Members who have left keep their place**; the board names them `<@id>` in words and `name: null` in JSON.

## Not built (and not in L2/L3 unless the owner asks)

Seasons and resets (decision 10); link prefill from speedrun.com or therun.gg
([`therun-research-2026-10-09.md`](therun-research-2026-10-09.md)); attachments as proof (links only); caps on repeat
runs (decision 7); a DM on approval; a member withdrawing their own pending run; deleting a bounty (End only); more
than one bounty on a run; per-game boards; an announcement for the XP view; a sweep that re-announces a lost post.

## Gate (2026-10-09, branch `points-engine`, measured on the final code)

- `python -m pytest tests -q -p no:cacheprovider -n 8`: **12960 passed, 1 skipped** (`main` at `01d6e72b` collects
  12715 in a throwaway worktree; the branch 12961 — **+246 tests**).
- `python -m ruff check black_bloc tests site`: all checks passed.
- `scripts/site-gate.ps1 -Port 8823` (its own mock; `node site/mock/check.mjs`): *ok - 26 pages, 360 routes, 317 core
  settings, all keys present*; the mock stopped by the gate afterwards.
- Every `site/mock/*.test.mjs` (14): exit 0.

## Gate (layer 2, 2026-10-09, branch `points-discord`)

- `python -m pytest tests -q -p no:cacheprovider -n 8`: **13025 passed, 1 skipped**.
- `python -m ruff check black_bloc tests site`: all checks passed.
- `scripts/site-gate.ps1 -Port 8833` (its own mock; `node site/mock/check.mjs`): *ok - 26 pages, 360 routes, 346 core
  settings, all keys present*; the mock stopped by the gate (port free afterwards). Every `site/mock/*.test.mjs`
  (14): exit 0.

## What was NOT verified (layer 2)

- **Nothing met Discord.** The board, the form, the run ticket, the card's Approve/Reject, the Remove button in an
  archived thread, the post and the DMs are tested against fakes only. Whether a button under a message in an
  archived, locked thread still answers is Discord's behaviour and was not tried.
- A verifier who is not staff may not be able to SEE a run ticket's room (its overwrites are the staff roles), so
  deciding from the card may in practice be staff-only until the verifier role can see the modmail rooms — not tried.
- The modmail inbox panel's tag and card copy were exercised through the pure helpers and the card, not by opening
  `/modmail` against Discord.

## What was NOT verified (layer 1)

- Nothing met Discord — layer 1 has no Discord code; §G is a specification.
- No browser rendered anything — there is no page; the mock answers the shapes and simplifies (no event bounties'
  windows, tiers fixed at the shipped ones, no recompute of speedpoints).
- Schema 92 ran on fixtures only (a fresh file and a 91 file), not on the live database.
- Decision 4's reading (*next rank = next place up*) is the owner's, *to be confirmed by staff*.
- Concurrency is tested for two approvals of one run at once in one process (`asyncio.gather`), not across processes.
- The `/settings` panel and the Settings page were not opened to look at the 56 new keys.
- Pawpette's *"must show livesplit or IGT"* is a human check at approval; nothing reads the image.
