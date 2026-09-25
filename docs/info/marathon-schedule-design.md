# Marathon schedules — our people on a marathon stream, read off the posted schedule, re-read every half hour

> **Audience:** the build agent and reviewers. **Status:** TRACKED · 📐 **DESIGN (Fable, 2026-09-25 11:xx Phoenix)
> — dispatches to Opus as branch `marathon-schedule` AFTER `spotlight-ping-windows` merges** (it writes that
> build's `spotlight_ping_windows` table and calls its `pings_now` gate). Member request **#12** on the Requests page.
> **Last verified: 2026-09-25 11:xx** against `main` `84f94347` (v163 live) and three live fetches:
> the GDQ tracker — `GET https://tracker.gamesdonequick.com/tracker/api/v2/events/` answers `{count, next, previous,
> results[]}` with `id`, `short` (`AGDQ2027` is id **74**), `name`, `datetime`, `timezone`; `GET …/api/v2/runs/?event=74`
> answers the same envelope **paginated 500 a page** (`next` carries `limit=500&offset=500`), each run with `id`, `order`,
> `name`, `display_name`, `category`, `console`, `starttime`, `endtime`, `run_time`, `setup_time`, `anchor_time`,
> `twitch_name`, `runners[]` / `hosts[]` / `commentators[]` — each a talent `{id, name, stream, twitter, youtube,
> platform, pronouns}` (example: *blaster master*, runner **UraniumAnchor**, `stream` `https://twitch.tv/uraniumanchor`).
> Horaro: **horaro.org is a static archive as of 2026; live schedules moved to horaro.net** (its `/-/api` answers 410).
> Oengus: `GET https://oengus.io/api/v2/marathons/LSS26/schedules` answers `{data: [{id, marathonId, name, slug,
> published}]}` with **no lines inlined**; the v1 `…/api/v1/marathons/LSS26/schedule` answers `{id: 0, lines: null}` for a
> v2 marathon. ⚠️ The Horaro.net and Oengus line shapes are NOT verified — §D says what the builder must capture live.
> Code: `cogs/content/golive.py` — `link_owner(db, login)` `:273` (a Twitch login → the member who linked it),
> `all_links` `:268`; `pings.announced_fan_role(bot, guild, user_id)` `:336` (a member's own ping role);
> `cogs/content/spotlight.py` — `open_session` `:262`, `refresh_session_info` `:253` (the channel's live TITLE, re-read
> every `spotlight_poll_minutes`), `_pin` / `_unpin` (the pin helpers), `_post` `:1050` (the on / shadow posting rule);
> `black_bloc/raidtrain.py` — `due_reminders` `:415`, `missed_reminders` `:436` (the reminder-that-is-too-late precedent),
> `render_lineup` `:347`; `cogs/content/raidtrain.py` — the one-command panel pattern (`RaidPanel` `:973`,
> `TrainPick` `:1962`, `MoveButton` `:1901`); `api/tools/raidtrain.py` (a feature router, `:170–352`);
> `site/public/assets/page-raidtrain.js` + `shell.js:GROUPS` `:8` (the *Runs the cookout* nav group);
> `black_bloc/youtube.py:214` (the `User-Agent` + client the bot already fetches pages with); `black_bloc/logkinds.py`
> `FEATURES` `:38` / `HEADS` `:62` / `FEATURE_PAGES` `:124`; `black_bloc/loops.py` (`wait_ready`, `Reconciler`);
> `black_bloc/timezones.py:unix` `:82`. Schema is **58** on `main`; `spotlight-ping-windows` takes **59**; this build
> takes **60**. ⚠️ Secret NAMES only.

## The ask, verbatim

**Request #12 (Sky, 2026-09-21 00:11, status `open`):** *"Dynamic Scheduling Shoutouts! I want a way to know during a
marathon or event when runners who are apart of this community are scheduled to do a run. A notification somewhere
about those members that dynamically updates based on a posted schedule such as the GDQ schedule page would be great.
This could also come with time based reminders such as live in 2 hours for those people."* Why: *"Sometimes I look
through the marathon schedule and can't quickly pick out when someone is going to be on stage or doing an
interview/video. This will allow us to give the maximum amount of support to participants as well as give production
a bit of a break from having to post it daily as reminders."*

**Owner (2026-09-25 10:4x Phoenix):** *"I want to work on building the last request for highlighting when BaF members
are on a marathon stream. We will need to be able to scrape a site that has the marathon schedule for twitch/username
and add those to a dynamic schedule. The other caveat is that the schedules sometimes get delayed or mixed up, so we
need to be constantly checking every maybe 30 - 1h?"*

## A. The model — a marathon, its runs, and who of ours is in them

**`marathons`** (new table, `SCHEMA` bootstrap): `id, guild_id, name, schedule_url, source` (`gdq` / `horaro` /
`oengus`), `source_ref` (the tracker event id, the `event/schedule` slugs, the Oengus marathon id + schedule id),
`spotlight_id` (nullable — the channel row it airs on, e.g. GamesDoneQuick `id 3`; a marathon with none links each
run's own runner URL instead), `starts_at, ends_at` (DERIVED from the schedule on every fetch: first run's start, last
run's end — never typed), `active INTEGER NOT NULL DEFAULT 1` (paused = kept, not fetched), `poll_minutes` (NULL = the
key), `board_channel_id, board_message_id, board_pinned`, `last_fetched_at, last_fetch_ok INTEGER, last_error TEXT,
fetch_failures INTEGER NOT NULL DEFAULT 0, fetch_hash TEXT`, `added_by, added_at`, `UNIQUE (guild_id, schedule_url)`.

**`marathon_runs`**: `id, marathon_id, external_id TEXT` (the source's own run id; **`UNIQUE (marathon_id,
external_id)`** — this is what makes a re-fetch a diff and not a re-insert), `order_no, game, category, runners_text`
(the names joined, for display), `people TEXT` (JSON: `[{name, login, user_id, part}]` — `part` is `runner` / `host` /
`commentator`; `login` the Twitch login the source gave or NULL; `user_id` the matched member or NULL),
`scheduled_at, ends_at, run_seconds`, `previous_scheduled_at, moved_at`, `state` (`upcoming` / `live` / `done` /
`dropped`), `live_at, live_because` (`title` / `schedule` / `staff`), `done_at`, `shout_message_id, shout_channel_id`,
`reminders_sent TEXT` (JSON list of the minute marks already posted), `first_seen_at, last_seen_at`.

**`marathon_people`**: `id, guild_id, marathon_id` (NULL = every marathon), `runner_name TEXT` (lower-cased, trimmed),
`user_id, added_by, added_at`, `UNIQUE (guild_id, marathon_id, runner_name)` — the staff pairing for a schedule that
names a person without a Twitch link (a host, a commentator, an interview). **Staff get the final say:** a pairing wins
over the automatic match, and **Unpair** reverses it.

**Matching, one pure function `match_people(people, links, pairings)`** in `black_bloc/marathon.py`, run on every
fetch for every run: for each person, (1) their `login` (from `stream` / `twitch_name` / a Twitch connection) →
`link_owner` over the guild's `golive_links` (case-insensitive); else (2) their name → `marathon_people` (this
marathon's row first, then the every-marathon row); else nothing. Hosts and commentators are matched too when
`marathon_match_hosts` is on (Sky: *"on stage or doing an interview/video"*). A member found on a run that had none
logs `marathon.run_matched` (routine). **A run is *ours* when any of its people has a `user_id`.**

## B. The fetch — every half hour while it matters, and a diff, never a wipe

One `tasks.loop` on the cog (through `loops.wait_ready`, a loop guard per KI-24, one `Reconciler` at boot), ticking
every minute and deciding per marathon whether a fetch is DUE: an active marathon is **near** from `marathon_lead_days`
(7) before `starts_at` until one day after `ends_at`, and near ones re-fetch every `marathon_poll_minutes` (**30**,
10–120; the row's `poll_minutes` overrides); far ones every `marathon_far_poll_hours` (24). A fresh row fetches at
once. One HTTP GET per fetch (the tracker's pagination followed, `limit=500`), through the same client and
`User-Agent` `black_bloc/youtube.py:214` uses, 20 s timeout, never raising out of the loop.

**The diff, by `external_id`:** a run not seen before is inserted (`upcoming`); a run whose `scheduled_at` moved by at
least `marathon_move_minutes` (5) gets `previous_scheduled_at` + `moved_at` and, if it is ours, logs
`marathon.member_run_moved` (**IMPORTANT** — this is the *delayed* case a person wants to hear about, with the old and
new times in the row); a run missing from the fetch becomes `dropped` (never deleted — its shout and reminders are
history); a `dropped` run that reappears goes back to `upcoming`. Game / category / people changes are written in
place. `starts_at` / `ends_at` on the marathon are recomputed; `fetch_hash` (sha256 of the normalised run list) lets an
unchanged fetch log `marathon.fetched` with `changed: false` and touch nothing else. A failed fetch increments
`fetch_failures`, keeps every run as it was, and logs `marathon.fetch_failed` — routine for the first two, **IMPORTANT
on the third consecutive** (the schedule is stale and nobody would know); a success resets the count. The page and the
panel show *last read 12 min ago* / *could not be read since 09:40 — {last_error in words}*.

**The ping window (the `spotlight-ping-windows` hook).** After every successful fetch of a marathon with a
`spotlight_id`, upsert ONE `spotlight_ping_windows` row `(source = 'marathon', source_id = marathon.id)` on that
channel: `starts_at − marathon_window_slack_hours` (2) to `ends_at + slack`, note = the marathon's name. Pause, Remove
and a marathon losing its channel delete that window. This is how *GDQ pings only during events* becomes automatic:
the owner sets GDQ's ping mode to *During events* once, and every marathon staff add opens the window for its dates.

## C. Live, late, and out of order — the two signals

**Signal 1, the schedule.** The re-fetch is what tracks an official delay: the GDQ tracker re-times every later run
as the day slips, so a 30-minute re-read is a schedule that is at most 30 minutes wrong.

**Signal 2, the channel's live title** (`marathon_title_confirms`, bool, true). A marathon with a `spotlight_id` whose
channel has an open spotlight session has a `title` the spotlight poller refreshes every five minutes (KI-39 made that
edit-happy; here it is the point). On every minute tick, for each near marathon: normalise the title (lower-case,
strip punctuation) and look for a run whose normalised `game` (or `display_name`) is in it, tie-broken by a runner's
name being in it, preferring the run nearest its scheduled time. A hit makes that run **`live`** (`live_because:
title`) and every earlier `upcoming` run **`done`** without a shout — the *mixed up* case; a skipped run of OURS logs
`marathon.run_skipped` (**IMPORTANT**, so staff can **Shout it now** by hand). A run whose `scheduled_at` has passed
with no title hit stays `upcoming` (the run before it is running long) until `marathon_late_grace_minutes` (90) has
passed, then goes `live` on the schedule alone (`live_because: schedule`). Without a channel, or with the key off, the
schedule alone decides at `scheduled_at`. A `live` run becomes `done` when the title moves on to a later run or, failing
that, at `ends_at + grace`.

## D. The three posts — all into `marathon_channel_id` (blank = `golive_channel_id`), `marathon_mode` off / **shadow** / on exactly as spotlight posts (shadow → `shadow_channel_id` with the rehearsal note; `marathon.would_*` rows)

| Post | When | What |
|---|---|---|
| **the board** — ONE message per marathon, edited in place | posted after the first fetch that finds a run of ours (or on **Post the board** by staff); edited on every fetch that changed a run of ours, on every state change, and when a pairing changes; pinned when `marathon_pin_board` (true) through the spotlight pin helpers; unpinned one day after `ends_at`; `marathon.board_posted` / `board_refreshed` / `board_failed` | `marathon_board_template` head (`{marathon} {count} {starts} {ends} {url}`) + one `marathon_board_line_template` per run of ours in schedule order (`{member} {game} {category} {when} {relative} {part} {state}` — `{when}` and `{relative}` are Discord `<t:unix:f>` / `<t:unix:R>` so every reader sees their own zone; `{member}` is the mention — the board is the one post that may mention members without pinging: `AllowedMentions.none()`), or `marathon_board_empty_line` when none matched yet |
| **a reminder** per run of ours per mark | at each mark in `marathon_reminder_minutes` (text, default `120, 15`; a validator refuses anything but 1–6 integers 1–1440) once `now ≥ scheduled_at − mark` and that mark is not in `reminders_sent`; a mark older than `marathon_reminder_stale_minutes` (30) past its moment is SKIPPED and logged (`marathon.reminder_skipped`), never posted late — the raid-train `missed_reminders` rule; a run that moved forgets marks that are now in the future again | `marathon_reminder_template` (`{member} {game} {category} {in} {when} {url} {marathon} {part}`); mentions, when `marathon_reminder_pings` (true): the member's own fan role (`pings.announced_fan_role`) AND the marathon channel's ping role through `pings_now` (the ping-windows gate) — never the global `golive_ping_role_id` (this is not a go-live); `marathon.reminded` |
| **the shoutout** | the moment a run of ours becomes `live` (§C); `shout_message_id` written in the same transaction the state flips, so a restart re-posts nothing | `marathon_live_template` (`{member} {game} {category} {url} {marathon} {part}`; `{url}` is the marathon channel's URL when it has one, else the runner's own); the same mention rule as a reminder; `marathon.shouted`. When the run is `done` and `marathon_edit_done` (true), the shout is edited to `marathon_done_template` (past tense, no mention), `marathon.run_done` |

`{part}` renders through `marathon_part_runner` / `marathon_part_host` / `marathon_part_commentator` (three text keys,
*runs* / *hosts* / *is on commentary*). Every posted word is a key (owner rule); panel and page words are constants
in `black_bloc/marathon.py`.

## E. Sources — `black_bloc/marathon_sources.py`, pure, one reader per site — **GDQ ONLY in this build**

> ✅ **Owner decision, 2026-09-25 11:1x Phoenix, verbatim:** *"seeing that there is an api thats good to know. Lets start
> with the GDQ since thats the biggest one. The rest we can look at in the future."* So: this build ships the **GDQ
> tracker reader only**. `read_url` recognises the GDQ forms below and refuses every other host in words
> (`marathon_unknown_site`: *For now I can read the GDQ schedule only — that link is something else.*). The `source`
> column, the `Run` / `Person` shapes and the one-reader-per-site layout stay exactly as written so horaro.net and
> oengus.io are a later reader each, not a redesign; the two paragraphs about them below are the PARKED spec for that
> day and are **not built now** — open calls 2 and the Horaro / Oengus fixtures fall away with them.

`read_url(url) -> (source, ref) | refusal` recognises: **GDQ** — `https://gamesdonequick.com/schedule/<id>`,
`https://tracker.gamesdonequick.com/tracker/event/<id>` (and an event short such as `AGDQ2027`, resolved once through
`/api/v2/events/?short=`); **Horaro** — `https://horaro.net/<event>/<schedule>` (the `.json` export beside it, or
`/-/api/v1/schedules/…` — ⚠️ the builder fetches ONE real horaro.net schedule and records the working path and shape
in Deviations); **Oengus** — `https://oengus.io/marathon/<id>/schedule` (v2: `/api/v2/marathons/<id>/schedules` for the
published schedule's id, then its lines — ⚠️ the builder finds the lines endpoint on a live marathon from
`/api/v2/marathons/for-home`, records it, and notes whether runners expose a Twitch connection); anything else →
`marathon_unknown_site` in words (*I can read the GDQ schedule, horaro.net and oengus.io — that link is none of them.*).
Each `parse_<source>(payload) -> list[Run]` (`Run(external_id, order, game, display_name, category, starts_at,
ends_at, run_seconds, people=[Person(name, login, part)])`) is pure and tested against a fixture the builder captures
live and trims to ~10 runs under `tests/fixtures/marathon/`. The GDQ login comes from `runners[].stream`
(`twitch.tv/<login>`, through `golive.twitch_login_from_url`) or the run's `twitch_name`; hosts and commentators from
their lists. All times are stored UTC ISO; the tracker's `starttime` carries an offset already.

## F. Doors — one command, one page, staff moves that reverse every stored state

**The site — `marathons.html` + `page-marathons.js`**, in `shell.js:GROUPS` *Runs the cookout* after Raid trains
(`feature: 'marathon'`, icon `navMarathon` in `ui.js`), `FEATURE_PAGES['marathon'] = 'marathons.html'`. Sections: the
list (name · source · `<dates>` · state *far / near / live / over / paused* · runs of ours N of M · last read · fetch
trouble in words); **Add a marathon** (`askForm`: name, schedule URL, the channel — a select of channel rows from
`/api/golive/spotlight` showing *#name · Category*-style words, optional); per-marathon drawer: the runs table (every
run; ours highlighted; chips *Ours* / *All*; columns when · game · category · people · state · moved), **Refresh now**,
**Pause** / **Resume**, **Post the board** / **Refresh the board**, **Remove** (confirm), **Pair a runner…** (an unmatched
name from this schedule, or typed → a member picker) and **Unpair** on each pairing, **Shout it now** on a run of ours
that is `upcoming` or `live` without a shout. Settings: a *Marathons* drawer on `settings.html` placing every key
(`placeSettings`); the join fixture gains the namespace (KI-36).

**Routes** (`api/tools/marathons.py`, staff-gated, refusals in words): `GET /api/marathons`, `POST /api/marathons`
(`name`, `schedule_url`, `spotlight_id?`; refuses an unknown site, a duplicate URL, a URL that will not read — with
the fetch's reason), `GET /api/marathons/{id}` (+ runs + people + pairings), `PATCH /api/marathons/{id}` (`name`,
`spotlight_id`, `active`, `poll_minutes`), `DELETE /api/marathons/{id}`, `POST …/refresh`, `POST …/board`,
`GET` / `POST …/people` (`runner_name`, `user_id`), `DELETE …/people/{person_id}`, `POST …/runs/{run_id}/shout`,
`POST …/runs/{run_id}/done`. Contract rows + mock rows: *AGDQ 2027* (near, ~12 runs, 3 ours — one moved 40 min, one
live), *Halo Fest* (over), one paused.

**Discord — `/marathon`** (cog **24**, `black_bloc/cogs/content/marathon.py`, `TOP_LEVEL_NOW` + 1, a guide row if
`tests/test_guides.py` guards one per command). Member root card: **Ours next** — the next five runs of ours across
near marathons with `<t:…:R>`, and **My runs**. Staff half: **Add a marathon…** (modal: name, URL, channel login —
blank for none), a marathon select → Refresh now / Pause · Resume / Post the board / Remove (confirm) / **Pair a
runner…** (a select of this schedule's unmatched names, then a `UserSelect`). Nothing a member can press changes
state.

## G. Keys — namespace `marathon_` (a NEW settings group; the `/settings` picker's Find box already handles > 25 groups), registry + mock + labels + `placeSettings` + `marathon_log_level` from the log-level family + `marathon_panel_minutes` like the other panels

Behaviour: `marathon_mode` (off / **shadow** / on), `marathon_channel_id` (channel, blank → go-live channel),
`marathon_poll_minutes` (30, 10–120), `marathon_far_poll_hours` (24, 1–168), `marathon_lead_days` (7, 1–60),
`marathon_move_minutes` (5, 1–120), `marathon_title_confirms` (bool, true), `marathon_late_grace_minutes` (90, 0–360),
`marathon_match_hosts` (bool, true), `marathon_reminder_minutes` (text, `120, 15`), `marathon_reminder_pings` (bool,
true), `marathon_reminder_stale_minutes` (30, 1–240), `marathon_pin_board` (bool, true), `marathon_edit_done` (bool,
true), `marathon_window_slack_hours` (2, 0–24). Words: `marathon_board_template`, `marathon_board_line_template`,
`marathon_board_empty_line`, `marathon_reminder_template`, `marathon_live_template`, `marathon_done_template`,
`marathon_part_runner`, `marathon_part_host`, `marathon_part_commentator`, `marathon_unknown_site`,
`marathon_already_added`, `marathon_could_not_read`, `marathon_no_runs_yet`. Template validators refuse an unknown
`{…}` the way `spotlight_bump_template`'s does. Twenty-eight keys plus the two family keys.

## H. Logging — a new feature `marathon` (`FEATURES`, `HEADS`, `FEATURE_PAGES`, a Logs chip)

`marathon.added / removed / paused / resumed / channel_set / paired / unpaired` (routine), `marathon.fetched`
(routine, `changed`, counts), `marathon.fetch_failed` (routine; **IMPORTANT** at the third consecutive),
`marathon.schedule_changed` (routine: added / moved / dropped counts), `marathon.member_run_moved` (**IMPORTANT**),
`marathon.run_matched`, `marathon.run_live`, `marathon.run_done`, `marathon.run_skipped` (**IMPORTANT** when ours),
`marathon.board_posted / board_refreshed / board_failed` (failed IMPORTANT), `marathon.reminded / reminder_skipped`,
`marathon.shouted / shout_failed`, `marathon.window_set / window_dropped`, and the `would_*` twins of every post in
shadow. Every row carries `marathon_id`, `run_id` where there is one, and `member_id` on the member ones.

## I. Tests, docs, gate

`tests/test_marathon.py` (pure: `match_people` by login, by pairing, pairing wins, hosts off; the diff — new / moved
under and over the threshold / dropped / reappeared; the title match — game hit, runner tie-break, nearest-in-time,
earlier runs done, no hit inside grace, schedule-alone after grace; `due_marks` — each mark once, a moved run re-arms
a mark, a stale mark is skipped; the board / reminder / shout / done renders with every placeholder and with a bad
template), `tests/test_marathon_sources.py` (the three parsers against the captured fixtures; `read_url` for every
accepted form and the refusal), `tests/cogs/content/test_marathon.py` (a fetch inserts, a re-fetch diffs, a failed
fetch keeps the runs and counts, the third failure is IMPORTANT; the board posts once then edits; the reminder fires
at the mark and not before, once, and not when stale; the shout fires on the title flip, its message id lands with the
state, a restart re-posts nothing; a later title marks the earlier run done and logs the skip; shadow → the shadow
home and `would_*`; the window upsert and its removal on pause / remove; near / far cadence), `tests/api/tools/
test_marathons.py` (every route, the staff gate, the refusals), `tests/api/test_contract.py`, `tests/storage/
test_db.py` (60), `tests/test_logkinds.py` / `test_settings_store.py` / `test_bot.py` count guards (cog 24, the new
feature, the keys, `TOP_LEVEL_NOW`), `golive-join.test.mjs` or a `marathons-join` fixture as the page pattern
dictates, `check.mjs` (23 pages). Both `pytest -n 8` orders, `ruff check black_bloc tests site`, the ES-module parse,
the node tests, a mock port of the builder's own. ⚠️ KI-26, KI-36, KI-37 as documented. Docs: `code-notes.md`;
this doc's `## Deviations` + `## What was NOT verified`; `architecture.md` (cog 24, schema 60, the tables, the keys,
the routes, the page); `docs/info/README.md` (one row); `docs/access/site.md` (23 pages); `spotlight-ping-windows-design.md`
one dated line (the marathon source of a window is live); `sweeps.md` rows (a: add AGDQ 2027 by its schedule URL on
the Marathons page → runs appear, ours highlighted; b: pair a host's name to a member → the board gains the line;
c: `marathon_mode = shadow` → the board and a reminder land in `#welcome-test` with the note; d: a live GDQ title
naming one of our games flips the run live and shouts; e: `/marathon` shows *Ours next*; f: the GDQ row's ping window
appears on the Go-live page drawer with the marathon's name). NOT `TODO.md` / `DONE.md` / `deploys.log` /
`KNOWN_ISSUES.md`. ⚠️ Migrate before deploy: three tables through the bootstrap.

**Build order (commit at each):** storage → `marathon_sources.py` + fixtures → `marathon.py` (pure) → the cog (fetch,
diff, states, posts, window) → the API → the page + mock + contract → `/marathon` → docs. If headroom is tight, the
first four are one dispatch and the last four another; the seam is the API.

## Open calls the build must make and record in Deviations

1. Whether the GDQ schedule page's `<id>` is the tracker event id (it is for the tracker's own `/tracker/event/<id>`;
   check `gamesdonequick.com/schedule/74` resolves to AGDQ 2027 — if not, resolve through `/api/v2/events/`).
2. The working horaro.net and oengus.io line endpoints and whether either exposes a Twitch login per runner; a source
   that names people without a login is still useful through pairing.
3. Whether the title match should also read the GDQ run's `display_name` and the runner's name — build it to read all
   three and say what the captured titles look like.

## Deviations

*(the build agent writes this)*

## What was NOT verified

*(the build agent writes this)*
