# Personal best feed — a linked member's verified speedrun.com PB, posted once

> **Audience:** the build agent, reviewers and future Claude sessions. **Status:** TRACKED ·
> 🔨 **BUILT on branch `pb-feed`** (off `main` `0d159774`), NOT merged, NOT deployed.
> **Last verified: 2026-10-05** — by the hermetic test suite, `ruff`, the node tests and the local
> mock (figures at the foot under *Gate*); the speedrun.com facts in §A by reading the official
> API docs and by three real read-only GETs that day. ⚠️ **NOT checked:** nothing here has met
> Discord, and the bot's own client has never called speedrun.com — see *What was NOT verified*.
> ⚠️ Secret NAMES only (this feature has no secret: the read endpoints are anonymous).

## The ask

Owner, 2026-10-05, verbatim, picking from a list of popular bot features: *"Let's build 1, 8, 10"*
/ *"We'll leave them in shadow for now"*. **1** = when a linked member gets a new personal best
on speedrun.com, the bot posts it. Two owner decisions, both final:

1. Members are found **automatically from the Twitch login they already linked** (`golive_links`),
   with an opt-out.
2. A personal best is posted **only once speedrun.com has VERIFIED it**. Never on submission;
   nothing ever has to be taken back.

## A. speedrun.com — what was confirmed, and what the docs leave unstated

API: REST v1, `https://www.speedrun.com/api/v1`. Docs: <https://github.com/speedruncomorg/api>
(`README.md`, `throttling.md`, `version1/README.md`, `users.md`, `runs.md`, `pagination.md`,
`embedding.md`), read 2026-10-05.

| Fact | Source |
|---|---|
| Reads are anonymous: *"Most of the API is read-only and anonymous"* — no key | docs `README.md` |
| *"If possible, please set a descriptive `User-Agent` HTTP header"* | docs `README.md` |
| *"Each IP is allowed to perform 100 requests per minute"*; a throttled request answers **420** | docs `throttling.md` |
| Collections default to 20 elements, `max` 1–200, `offset`; the last page is the one whose `pagination.size` is under `max` | docs `pagination.md` |
| `GET /users` takes `twitch` (*"searches for Twitch usernames"*), `lookup`, `name`, `speedrunslive` | docs `users.md` |
| `GET /users/{id}/personal-bests`: *"a list of runs, representing the Personal Bests of the given user. This will not include obsolete runs."* Each item is `place` + `run`; `top`, `series`, `game` filter it; *"All embeds that are available for runs are available here as well"*, placed beside the run | docs `users.md` |
| A run's `status.status` is `new`, `verified` or `rejected`; a verified run has `verify-date`, which *"older runs may have null"*; `times.primary_t` is the leaderboard time in seconds; `values` maps variable id → value id; `level` is null for a full-game run | docs `runs.md` |
| An embedded resource is wrapped: `"game": {"data": {…}}`; embeds nest with a dot (`category.variables`) | docs `embedding.md` |
| `GET /users?twitch=zfg1` → one user, `names.international` `zfg`, `twitch.uri` `https://www.twitch.tv/Zfg1` — the stored login differs from the query **in case only** | real GET 1 |
| `GET /users?twitch=zfg` (a prefix of that login) → **zero** users: the `twitch` filter is an exact match, not a search | real GET 3 |
| `GET /users/{id}/personal-bests?embed=game,category,level` → 61 items in ONE response with **no `pagination` object**; every `status.status` was `verified`; `verify-date` was `null` on a 2013 run; a full-game run's `level` embed is `{"data": []}`; `place` is an integer | real GET 2 |

The three GETs used the public runner **zfg** and are trimmed into `tests/fixtures/speedrun/`.

**Unstated by the docs, and how the code treats each:**

- Whether `twitch` matches exactly or case-sensitively. Observed exact and case-insensitive; the
  code does not rely on it — `pb_match.exact` re-checks every returned user's own `twitch.uri`.
- Whether personal-bests can ever contain a run that is not verified. Observed none; the code
  filters on `status.status == "verified"` regardless.
- Whether personal-bests is paginated. Observed not (61 items, no pagination object). The client
  asks `max=200` and follows `pagination` only if one is present, up to 5 pages.
- Whether the nested embed `category.variables` is honoured on this endpoint. ⚠️ **ASSUMED** from
  *"all embeds that are available for runs"* — the three GETs were spent before it could be
  tried. The client asks for it and, on a `400`, falls back for the life of the process to
  `game,category,level`, which was confirmed. Without it a post names no sub-category.
- Error bodies and the meaning of `404` (no `errors.md` exists). `404` on a user's personal-bests
  is read as *that speedrun.com account is gone*.
- Whether `429` is ever sent. Treated like `420`.

## B. Matching — `black_bloc/pb_match.py`

A match is a row in `pb_matches`: the member, the Twitch login it came from, the speedrun.com
user id, name and link, **how it was made** (`source`: `auto` | `staff`), its **state**
(`matched` | `none` | `opted_out` | `blocked`) and who put it in that state (`state_by`:
`auto` | `staff` | `member`).

- **Exact or nothing.** `GET /users?twitch=<login>&max=20`, then keep only users whose own
  `twitch.uri` ends in that login, compared case-folded. Exactly one → a match. Zero → no match.
  Two or more → **no match** (`ambiguous`), never a pick. No name similarity anywhere.
- **Automatic** for every member with a `golive_links` row who is in the server, while
  `pb_feed_auto_match` is true. A member with no match is looked up again after
  `pb_feed_rematch_days`.
- **Never automatic** for a member who is `opted_out` or `blocked`. Those rows are skipped before
  any request is made.
- **The link moved.** An `auto` match whose member has since changed or removed their Twitch link
  is undone (state `none`) and looked up again under the new login. A `staff` match does not
  depend on the link.
- **One speedrun.com account, one member** (checklist 16): `pb_matches` has a partial unique index
  on `(guild_id, src_user_id)`; a second claim is refused in words for staff and left `none`
  (`pbfeed.match_refused`) for the automatic path.
- A changed or removed match **wipes that member's baseline**, so the next sight is a first sight.

## C. What is news — `black_bloc/pb_news.py`, a pure function

`news(baseline, fetched, *, since, now, max_age_days)` → what to post and what to record quietly.

- Only runs whose `status` is `verified` are read at all.
- **First sight is silent.** While `pb_matches.baseline_at` is NULL the whole fetched list is
  written to `pb_runs` and nothing is posted (`pbfeed.baseline`).
- A fetched run is **news** only when ALL hold: its run id is not one already stored for this
  member; its slot (game + category + level + sub-category values) is new **or** its time is lower
  than the stored one; its `verify-date` is present and **not before `baseline_at`**; and it was
  verified no more than `pb_feed_max_age_days` ago.
- Everything else is recorded quietly: the same run with a different `place` (other people's runs
  move it daily), a different run that is not faster (a rejected PB falling back to the older
  one), a run verified before the baseline (a leaderboard re-organised under new category ids),
  a run with no `verify-date`.
- **Stored slots are never deleted by a look.** An empty or short answer therefore cannot arm a
  replay; a restart reads the same table; an outage changes nothing.
- A posted run is claimed in `pb_posts` (`UNIQUE (guild_id, run_id)`) **before** the send, so two
  looks cannot post one run twice (checklists 6, 37).
- At most `pb_feed_max_posts` posts per member per look; the rest are recorded as `held`
  (`pbfeed.held_back`) and never posted later.

## D. The post

One embed per new PB: title `pb_feed_post_title`, description `pb_feed_post_text`, the embed's
link is the run. Fields the templates may use: `{member}` (a mention — it does not ping, see
below), `{name}` (display name), `{runner}` (speedrun.com name), `{game}`, `{category}` (level,
category and sub-category values joined), `{time}`, `{place}`, `{place_line}`
(`pb_feed_place_text` filled, or nothing when the API gave no place), `{link}`. A template that
cannot be filled falls back to the shipped one with a log line (checklist 17).

- `AllowedMentions.none()` on every send. With `pb_feed_ping_role_id` set, the role is put above
  the embed and is the only mention allowed. A rehearsal copy never pings.
- `pb_feed_mode` = `off` | `shadow` | `on`, default **`shadow`**.

| Mode | Looks | A new PB |
|---|---|---|
| `off` | none — no request leaves the bot | — |
| `shadow` | yes | a rehearsal copy in `pb_feed_shadow_channel_id`, else `shadow_channel_id`, else the log channel (`black_bloc/shadow.py`), under the rehearsal note naming the real channel; `pbfeed.would_post` |
| `on` | yes | posted in `pb_feed_channel_id`; `pbfeed.posted`. **Blank is a refusal**, in words: `pbfeed.post_failed`, nothing guessed |

A failed or refused post is recorded on `pb_posts` (`outcome` `failed`, the reason) and is **not
retried**: the baseline has moved on, which is what stops a retry loop.

## E. Polling — `black_bloc/pb_looks.py`

- One loop, a tick a minute. A member is due when their last look is older than
  `pb_feed_interval_minutes` (default **60**, floor **15**).
- **Spread, not a burst:** a tick takes at most `ceil(people ÷ interval minutes)` members,
  oldest look first, and never more than **5** (`TICK_CAP`). After a boot the whole list is
  therefore worked through across one interval and stays spread.
- **Hard cap:** `pb_feed_cycle_requests` (default 120) requests in any one interval; at the cap
  the tick stops and `pbfeed.cap_reached` is written once per interval. Five requests a minute is
  5% of the documented 100.
- Every call has a 20-second timeout and the `User-Agent`
  `BlackBloc/<version> (Discord bot for a speedrunning community; <site origin>)`.
- **Backoff** on 420 / 429 / 5xx / timeout / no connection: 5 minutes, doubling to 6 hours.
  `pbfeed.look_failed` is written **once per outage** with the reason in words;
  `pbfeed.recovered` when a call works again. The state is in `pb_looks`, so a restart inside an
  outage does not log it a second time. Nothing raises out of the loop (checklist 28).
- Three different kinds for three different outcomes (checklist 2): `pbfeed.nothing_new` (one per
  interval that had looks and no news), `pbfeed.look_failed`, `pbfeed.posted` /
  `pbfeed.would_post`.

## F. Doors

- **Discord — `/pb`, one command for everybody** (the `/golive` shape). The card shows the
  member's own match and one button: *Do not post my personal bests* / *Post my personal bests*.
  Staff see the same card plus **Manage…**: a member picker, then per member **Unmatch**,
  **Block** / **Unblock**, **Set by hand…** (a modal taking a speedrun.com name), **Clear the
  opt-out**, **Look now**, and a link to the page. Every staff move is re-gated on staff.
- **Site — a page of its own, `pbs.html`** (*Personal bests*): the mode switch, everyone with a
  Twitch link or a match (how it was made, last looked, last PB seen), the same moves, recent
  posts, settings and logs.
- **API** (`black_bloc/api/tools/pbs.py`, staff only): `GET /api/pbs`, `PUT /api/pbs/{member}`
  (set by hand), `DELETE /api/pbs/{member}` (unmatch), `POST …/block`, `POST …/unblock`,
  `POST …/optin`, `POST …/look`. Both doors call `black_bloc/pb_moves.py` with `via`
  (checklist 34).

## G. Storage — schema **89**

Four tables appended to `SCHEMA` (additive; no column migration): `pb_matches`, `pb_runs` (the
baseline, one row per member per slot), `pb_posts` (what was posted, rehearsed, held or refused),
`pb_looks` (one row per server: the last look and the outage). They ride the database backup.

## H. Keys — all under `core`

`pb_` would have been a 26th setting group and `/settings` is at Discord's cap of 25; like
structure backup, every key is in `CORE_KEYS`. Operational: `pb_feed_mode`,
`pb_feed_channel_id`, `pb_feed_shadow_channel_id`, `pb_feed_ping_role_id`, `pb_feed_auto_match`,
`pb_feed_interval_minutes`, `pb_feed_cycle_requests`, `pb_feed_rematch_days`,
`pb_feed_max_age_days`, `pb_feed_max_posts`, `pb_feed_panel_minutes`. Wording: the post's four
templates, the sentences a member reads on `/pb`, and the answers staff get. Field names and
button labels on the staff half of the panel are constants in `black_bloc/pb_feed.py`.

## I. Log kinds — head `pbfeed`, filed under `core`

Routine: `pbfeed.matched`, `pbfeed.baseline`, `pbfeed.posted`, `pbfeed.nothing_new`,
`pbfeed.recovered`, `pbfeed.held_back`, `pbfeed.set_by_hand`, `pbfeed.unmatched`,
`pbfeed.blocked`, `pbfeed.unblocked`, `pbfeed.opted_out`, `pbfeed.opted_in`,
`pbfeed.opt_out_cleared`, `pbfeed.looked`. Shadow: `pbfeed.would_post`. Important:
`pbfeed.look_failed`, `pbfeed.post_failed`, `pbfeed.match_refused`, `pbfeed.cap_reached`,
`pbfeed.runner_gone`. Staff moves from the site carry the `web.` head through `kind_via`.

## Decisions made by the build beyond the brief

1. **A page of its own, keys under `core`** (§F, §H) — the structure-backup precedent. The Go-live
   page was the other candidate; its settings are placed by a hand-typed join fixture (KI-36) and
   it is already six sections. No `pbfeed` feature in `logkinds.FEATURES` (a 23rd would add a
   log-level key and a 26th group); the kinds follow `core_log_level`.
2. **`/pb` is a member command with the staff moves inside it**, not a second staff command.
3. **A better PLACE alone is never news** (§C). The brief said *a better time/place*; a place moves
   whenever anyone else's run is verified or rejected, without the member doing anything. Only a
   different, faster, verified run posts.
4. **`verify-date` must exist and be on or after the baseline** (§C), and no older than
   `pb_feed_max_age_days` (7). This is what stops a leaderboard re-organisation replaying years
   of runs.
5. **`pb_feed_max_posts`** (5) per member per look; the surplus is `held`, never posted late.
6. **A failed post is not retried** (§D).
7. **Sub-category names come from `category.variables`**, with a fallback when the API refuses the
   nested embed (§A). Only sub-category variables are named; other variables are not.
8. **Staff can clear a member's opt-out** (staff final say, logged `pbfeed.opt_out_cleared`).
   ⚠️ No DM is sent to the member when staff do it — a candidate follow-up.
9. **A member cannot set their own speedrun.com name.** It would let anyone claim a runner's
   account. `state_by` records `member` for the opt-out and opt-in only.
10. **`pb_feed_auto_match`**, **`pb_feed_rematch_days`**, **`pb_feed_cycle_requests`** are keys
    the brief did not name.
11. **A `404` on a matched runner** undoes the match (`pbfeed.runner_gone`) rather than counting
    as an outage.
12. **Members who have left the server are skipped, not deleted.**
13. **`/pb` hides while the mode is `off`** (`HIDDEN_WHEN_OFF`), like every other feature.
14. **Look now** by staff ignores the spread and the backoff, counts against the cap, and is
    refused in words while the mode is `off`.

## Not built

A DM to the member on a staff override; a member door on the site; game cover art on the post;
retrying a failed post; per-game or per-category filters; a log-level key of its own.

## Gate

Measured 2026-10-05 on branch `pb-feed`, before its docs commit:
`python -m pytest tests -q -p no:cacheprovider -n 8` **11190 passed, 3 skipped** (10911 on `main`);
`python -m ruff check .` clean; `node site/mock/check.mjs` **ok — 25 pages, 312 routes, 141 core
settings, all keys present** (24 / 305 / 101 on `main`); the twelve `site/mock/*.test.mjs` files
exit 0. By import: `len(KEY_TYPES)` **900** (860 + 40), `len(CORE_KEYS)` **141**,
`SCHEMA_VERSION` **89**, `len(COGS)` **29**. The Personal bests page was opened once in a browser
against the local mock: the members list, the mode switch, the filters, the recent posts and the
two folded sections drew, and the console showed no error.

## What was NOT verified

- **Nothing has met Discord.** No post, no rehearsal copy, `/pb` never opened in a client; the
  panel, the user picker, the modal and the link button were exercised through fakes only.
- **The bot's own client has never called speedrun.com.** `SpeedrunClient` was run only against
  fakes and the three trimmed fixtures. Unproven live: the nested `category.variables` embed (and
  the `400` the fallback expects if it is refused), the `lookup` filter used by Set by hand, a
  real `420`, and the size of a prolific runner's answer.
- **A run moving from `new` to `verified`** was never watched on the live API; that
  personal-bests lists only verified runs is an observation of one runner.
- **Whether a personal best appears in personal-bests at all before it is verified** — the code
  filters on status either way.
- The schema change has not run on the live database (four `CREATE TABLE IF NOT EXISTS`).
- On the site, no button was pressed in a browser (Set by hand, Match a member, Unmatch, Block,
  Look now, the mode switch); they are covered by `check.mjs` at the route level only. The page
  was not looked at on a phone-width screen.
- The mock's rows are a JavaScript stand-in; the real rows come from `api/tools/pbs.py`.
- TEST_MODE with a guard installed: one test, fakes.
- `ruff format --check` was not run. No guide was added to `guides_seed.json`. `/pb` was not
  added to the self-test's panel doors.
