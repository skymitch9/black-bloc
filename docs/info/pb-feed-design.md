# Personal best feed — a linked member's verified speedrun.com PB, posted once

> **Audience:** the build agent, reviewers and future Claude sessions. **Status:** TRACKED ·
> ✅ **MERGED to `main` at `c16deab1`** (merge commit `603b7d52`), **NOT deployed.** The review
> fixes of 2026-10-05 are on branch `pb-fixes` (off `c16deab1`) — see *Review fixes 2026-10-05*;
> that branch is NOT merged and NOT deployed. *Review fix 2026-10-07* (the post names the member) is
> on branch `pb-post-name`, verified 2026-10-07 by the suite, `ruff` and the local mock only.
> **Last verified: 2026-10-05** — by the hermetic test suite, `ruff`, the node tests and the local
> mock (figures at the foot under *Gate*); the speedrun.com facts in §A by reading the official
> API docs and by three real read-only GETs that day. ⚠️ **NOT checked:** nothing here has met
> Discord, and the bot's own client has never called speedrun.com — its transport has now read
> real HTTP answers, but only from a loopback server. See *What was NOT verified*.
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
  tried. The client asks for it and, ~~on a `400`, falls back for the life of the process to
  `game,category,level`~~ **(reversed 2026-10-05, review fixes):** on a `400` it asks the same
  question once more with `game,category,level`, which was confirmed. Only when that second
  question is answered was the `400` about the embed, and the client then runs without the
  variables for `EMBED_RETRY_SECONDS` (6 hours) before it asks for them again. If the plain
  question is refused with a `400` too, nothing flips and the refusal is that runner's own.
  Without the variables a post names no sub-category, and the slot carries **every** choice the
  run made behind a `?` (`game|category|level|?var=value,…`), so two runs with different choices
  are never compared; a run with no choices at all keeps the ordinary slot.
  `pbfeed.subcategories_untold` says so in the log each time the client falls back.
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
  The one exception (review fixes): a match undone by two `404`s keeps its rows and its
  `baseline_at`, and they are picked up again if the **same** speedrun.com account is matched
  back; a different account wipes them as before.
- **An opt-out is its own fact** (`pb_matches.opted_out_at`), not only a state. A block on top of
  it does not erase it: an unblock goes back to `opted_out`, the automatic match skips the row,
  and Set by hand is refused. Only the member's own **Post my personal bests** or staff's
  **Clear the opt-out** ends it.

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
- A look that recorded runs without posting them because they were `too_old`, `before_baseline`
  or `undated` writes one routine row, `pbfeed.not_news`, with the count by reason, and keeps
  the last such counts on the member's row (`pb_matches.quiet`, shown on the page).
- A claim that no look settled — the process stopped between the claim and the send — becomes
  `unconfirmed` at the first tick after a boot, with one `pbfeed.unconfirmed` row; it is listed
  with the posts and never sent again. A post that cannot even be built is `failed`, in words.

## D. The post

One embed per new PB: author line `pb_feed_post_author` (default `{name}`) beside the member's
avatar, title `pb_feed_post_title`, description `pb_feed_post_text` (default
`**{name}** ran **{game}** — …`), the embed's link is the run. *(Amended 2026-10-07 — see
Review fix 2026-10-07.)* Fields the templates may use: `{member}` (a mention — it does not ping,
see below; ⚠️ inside an embed Discord may show it as a raw id), `{name}` (display name), `{runner}` (speedrun.com name), `{game}`, `{category}` (level,
category and sub-category values joined), `{time}`, `{place}`, `{place_line}`
(`pb_feed_place_text` filled, or nothing when the API gave no place), `{link}`. A template that
cannot be filled falls back to the shipped one with a log line (checklist 17).

- `{name}` and `{runner}` are escaped like `{game}` and `{category}`: every bracket is escaped
  so no masked link survives, and `://` is broken with a zero-width space so no address links.
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
- **Hard cap:** `pb_feed_cycle_requests` (~~default 120~~ **default 400**, review fixes)
  requests in any one interval; at the cap the tick stops and `pbfeed.cap_reached` is written
  once per interval. The arithmetic: a tick takes at most 5 members, so the loop itself can
  send at most 5 × 60 = **300** requests in the default 60-minute interval — exactly 300
  members looked at once an hour, which 120 could not cover. 400 leaves 100 for lookups, a
  second page, the embed's second question and staff's Look now. 400 in 60 minutes is 6.7 a
  minute, **under 7% of the documented 100**; the key's ceiling of 600 over the 15-minute floor
  is 40 a minute. Look now and Set by hand are stopped by the same cap.
- Every call has a 20-second timeout and the `User-Agent`
  `BlackBloc/<version> (Discord bot for a speedrunning community; <site origin>)`.
- **Only an outage backs the server off.** 420 / 429 / 5xx / a timeout / no connection / an
  answer that is not JSON at all are the server's (`SpeedrunError.outage`). Everything else is
  **that member's own**: a refusal for that address (`403`, a `400` that is not the embed's), a
  `404`, an answer too large, `data` that is not a list, or a fault inside Black Bloc while
  reading them. It is written on their row in words (`look_error`), their look time advances,
  and the tick goes on to the next member. A member's lookup that fails the same way is left
  `none` with reason `trouble` and waits `pb_feed_rematch_days` like any other miss.
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
  **Unmatch**, **Block** and **Clear the opt-out** open a modal with one optional field, the
  reason; Set by hand's modal has the same field. A matched member's own sentence ends with one
  of `pb_feed_posting_on` / `_shadow` / `_off`, so it never promises a post the mode forbids.
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

The review fixes added four columns to `pb_matches`, in `SCHEMA` and in `ADDED_COLUMNS` (so a
database that already has the table gains them at boot; `SCHEMA_VERSION` stays **89**):
`opted_out_at` (backfilled from `updated_at` for rows already `opted_out`), `misses` (consecutive
`404`s), `gone_src_user_id` (the account a two-`404` undo removed) and `quiet` (the last
not-news counts, JSON). `pb_posts.outcome` gained the value `unconfirmed`; no column.

## H. Keys — all under `core`

`pb_` would have been a 26th setting group and `/settings` is at Discord's cap of 25; like
structure backup, every key is in `CORE_KEYS`. Operational: `pb_feed_mode`,
`pb_feed_channel_id`, `pb_feed_shadow_channel_id`, `pb_feed_ping_role_id`, `pb_feed_auto_match`,
`pb_feed_interval_minutes`, `pb_feed_cycle_requests`, `pb_feed_rematch_days`,
`pb_feed_max_age_days`, `pb_feed_max_posts`, `pb_feed_panel_minutes`. Wording: the post's four
templates, the sentences a member reads on `/pb`, and the answers staff get. Field names and
button labels on the staff half of the panel are constants in `black_bloc/pb_feed.py`.

The review fixes added **9** wording keys (40 → 49): `pb_feed_posting_on`,
`pb_feed_posting_shadow`, `pb_feed_posting_off`, `pb_feed_unblocked_opted_out_said`,
`pb_feed_dm_set`, `pb_feed_dm_unmatched`, `pb_feed_dm_blocked`, `pb_feed_dm_opt_out_cleared`,
`pb_feed_dm_no_reason`. Four shipped defaults changed: `pb_feed_cycle_requests` 120 → 400, and
`pb_feed_you_matched`, `pb_feed_you_set` and `pb_feed_opted_in_said` lost their promise of a post.

## I. Log kinds — head `pbfeed`, filed under `core`

Routine: `pbfeed.matched`, `pbfeed.baseline`, `pbfeed.posted`, `pbfeed.nothing_new`,
`pbfeed.recovered`, `pbfeed.held_back`, `pbfeed.set_by_hand`, `pbfeed.unmatched`,
`pbfeed.blocked`, `pbfeed.unblocked`, `pbfeed.opted_out`, `pbfeed.opted_in`,
`pbfeed.opt_out_cleared`, `pbfeed.looked`. Shadow: `pbfeed.would_post`. Important:
`pbfeed.look_failed`, `pbfeed.post_failed`, `pbfeed.match_refused`, `pbfeed.cap_reached`,
`pbfeed.runner_gone`. Staff moves from the site carry the `web.` head through `kind_via`.

Added by the review fixes — routine: `pbfeed.not_news`. Shadow: `pbfeed.would_dm`. Important:
`pbfeed.runner_missing` (a staff-set account that has answered `404` twice running),
`pbfeed.unconfirmed`, `pbfeed.subcategories_untold`, `pbfeed.dm_failed`.

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
   ~~⚠️ No DM is sent to the member when staff do it — a candidate follow-up.~~ **Reversed
   2026-10-05 (review fixes, S4):** the member is DM'd, as they are for Block, Unmatch and Set
   by hand — the standing owner rule is *"with a DM'd reason where a person is affected"*.
9. **A member cannot set their own speedrun.com name.** It would let anyone claim a runner's
   account. `state_by` records `member` for the opt-out and opt-in only.
10. **`pb_feed_auto_match`**, **`pb_feed_rematch_days`**, **`pb_feed_cycle_requests`** are keys
    the brief did not name.
11. **A `404` on a matched runner** ~~undoes the match (`pbfeed.runner_gone`)~~ is not an
    outage. **Reversed 2026-10-05 (review fixes, S6; checklist 32):** the first `404` is recorded
    on the row and asked again at the next look; the **second in a row** undoes an *automatic*
    match (`pbfeed.runner_gone`) and keeps its baseline for the same account; a *staff-set* match
    is never undone — the row says so in words and `pbfeed.runner_missing` is written once.
12. **Members who have left the server are skipped, not deleted.**
13. **`/pb` hides while the mode is `off`** (`HIDDEN_WHEN_OFF`), like every other feature.
14. **Look now** by staff ignores the spread ~~and the backoff, counts against the cap~~, and is
    refused in words while the mode is `off`. **Reversed 2026-10-05 (review fixes):** it waits
    out an outage backoff, is stopped by the cap, has a cooldown of
    `LOOK_NOW_COOLDOWN_MINUTES` (5, a constant) per member counted from that member's last look
    of any kind, and an outage it meets starts the backoff. Each refusal says when to try again.
    **Set by hand** is refused while `off` and is held by the backoff and the cap the same way.

## Not built

~~A DM to the member on a staff override;~~ (built 2026-10-05, review fixes) a member door on
the site; game cover art on the post; retrying a failed post; per-game or per-category filters;
a log-level key of its own.

## Review fixes 2026-10-05

An independent review of the merged feature; fixed on branch `pb-fixes`. Each finding, what
changed, and the test that pins it. Every test named here was run against `main` `c16deab1`
in a throwaway worktree and seen to fail there, except where the line says otherwise.

| # | Finding | What changed | Pinned by |
|---|---|---|---|
| **B1** | The real transport read only the first buffered piece of an answer, so a chunked 11 KB answer was `(200, None)` → a server-wide outage | `speedrun.whole_body` reads `iter_chunked` to the end, counting against `MAX_BODY_BYTES`, and refuses as too large only once the cap is really passed | `tests/test_speedrun.py::test_the_real_transport_reads_a_whole_answer_from_a_real_server` (a real aiohttp server on a loopback port; plain and chunked; 500 B / 11 KB / 110 KB) and `::test_the_real_transport_refuses_only_an_answer_that_really_passes_the_cap` |
| **S2** | One member's refusal, odd shape or a bug stopped the tick for everyone, and that member was retried first for ever | §E: only `SpeedrunError.outage` backs off; the rest is that member's `look_error`, their time advances, the tick goes on. The parser no longer raises on any shape (`words`, `seconds_of`, `place_of`; `urlsplit` guarded; `data` not a list is `MALFORMED`) | `tests/test_pb_looks.py::test_one_members_bad_answer_is_theirs_alone_and_the_feed_moves_on` (403, malformed, a bug), `::test_one_members_refused_lookup_does_not_hold_the_queue`; `tests/test_speedrun.py::test_no_malformed_shape_ever_raises_out_of_the_parser` (property style, over 500 shapes), `::test_a_time_that_is_not_a_real_number_of_seconds_is_no_personal_best`, `::test_a_profile_address_that_cannot_be_parsed_names_no_login`, `::test_personal_bests_that_are_not_a_list_are_that_runners_trouble_not_an_outage` |
| **S3** | Opt out → Block → Unblock silently ended the opt-out; two ticks later the member was matched again | §B: `opted_out_at` outlives a block; `pb_store.restore(ends_opt_out=…)` | `tests/test_pb_moves.py::test_an_opt_out_survives_a_block_and_an_unblock`, `::test_staff_cannot_set_an_account_over_an_opt_out_hidden_under_a_block`, `::test_only_the_member_or_the_explicit_staff_move_ends_an_opt_out`; `tests/api/tools/test_pbs.py::test_an_opt_out_survives_a_block_and_an_unblock_from_the_site` |
| **S4** | Clear the opt-out, Block, Unmatch and Set by hand told the member nothing | `pb_moves.tell`: one DM with what changed, staff's reason and how to undo their part; both doors take a reason. The pattern is `applications.send_dm`: in `shadow` (and `off`) nothing is sent and `pbfeed.would_dm` carries the text; in `on` a closed DM is `pbfeed.dm_failed` in words and the move stands | `tests/test_pb_moves.py::test_a_staff_move_that_affects_a_member_dms_them_the_reason_once`, `::test_closed_dms_are_logged_in_words_and_never_block_the_move`, `::test_while_the_feed_is_not_on_the_dm_is_logged_and_never_sent`, `::test_a_dm_never_carries_markdown_or_a_ping_from_the_reason`; `tests/test_pb_panel.py::test_unmatch_and_clear_ask_for_a_reason_before_they_act`; `tests/api/tools/test_pbs.py::test_a_reason_typed_on_the_site_reaches_the_member_and_the_row` |
| **S6** | One `404` wiped a match and its baseline, a staff-set one included | Decision 11 above | `tests/test_pb_looks.py::test_one_404_is_recorded_and_retried_and_wipes_nothing`, `::test_a_second_404_in_a_row_undoes_an_automatic_match_and_keeps_the_baseline`, `::test_a_match_staff_set_is_never_undone_by_404s_and_says_so_for_staff` |
| **S7** | The model's `/pb` line and the member's own sentences promised a post in `shadow` and `off` | The `/pb` line in `personas.FEATURES` claims nothing and tells the model not to; `pb_feed_posting_*` by mode; `pb_feed_opted_in_said` reworded. `/pb` stays offered in `shadow`: every other shadowed member feature keeps its command (`HIDDEN_WHEN_OFF` hides at `off` only) | `tests/test_personas.py::test_the_pb_line_never_promises_a_post_the_mode_may_forbid`; `tests/test_pb_panel.py::test_a_matched_member_is_never_promised_a_post_the_mode_forbids`, `::test_opting_back_in_while_rehearsing_promises_no_post`; `tests/test_pb_feed.py::test_no_sentence_a_member_reads_promises_a_post_unless_the_mode_is_on` |
| — | Runs absorbed as too old / before the baseline / undated left no trace | §C: `pbfeed.not_news`, `pb_matches.quiet`, a line on the page | `tests/test_pb_looks.py::test_runs_that_were_recorded_and_not_posted_are_counted_by_reason` |
| — | Look now ignored the cap and the backoff | Decision 14 above | `tests/test_pb_moves.py::test_look_now_has_a_cooldown_for_each_member`, `::test_look_now_respects_an_outage_backoff_and_starts_one`, `::test_look_now_and_set_by_hand_stop_at_the_request_cap` |
| — | Set by hand asked speedrun.com while `off` | Refused with `pb_feed_off_said`; the button is not drawn while `off` | `tests/test_pb_moves.py::test_set_by_hand_asks_speedrun_nothing_while_the_feed_is_off` |
| — | Any `400` dropped the nested embed for the life of the process, and without it two sub-categories shared a slot | §A | `tests/test_speedrun.py::test_a_400_that_is_not_about_the_embed_flips_nothing`, `::test_the_nested_embed_is_asked_for_again_after_a_while`, `::test_without_the_variables_two_sub_categories_are_never_one_slot`; `tests/test_pb_looks.py::test_running_without_the_sub_categories_is_said_once_in_the_log` |
| — | `{name}` and `{runner}` were not escaped | §D | `tests/test_pb_feed.py::test_a_display_name_or_a_runner_name_cannot_smuggle_a_link_into_a_post` |
| — | A crash between claim and send left a hidden `claimed` row | §C | `tests/test_pb_looks.py::test_a_claim_no_look_settled_is_said_once_at_boot_and_stops_hiding`, `::test_a_post_that_cannot_be_built_is_a_failure_in_words_not_a_stuck_claim` |
| — | The default cap (120 an hour) was under what 300 members need | §E, with the arithmetic | `tests/test_pb_feed.py::test_the_shipped_request_cap_covers_300_members_and_stays_far_under_the_limit` |
| — | `NAME_LIMIT` lived in two modules | One home, `pb_moves.py` | `tests/test_pb_panel.py::test_the_name_limit_has_one_home` |

**Decisions the fixes made beyond the review's words**

1. *An opt-out under a block is refused for Set by hand too*, not only skipped by the automatic
   match — otherwise Block → Set by hand would be a second way round the opt-out.
2. *The reason is optional on both doors.* A blank one is sent as `pb_feed_dm_no_reason`.
3. *No DM for Unblock.* It is in the member's favour and the review named four moves.
4. *In `off` the DM is logged like `shadow`*, never sent: nothing reaches a member unless the
   mode is `on`. ⚠️ A member whose opt-out staff cleared while rehearsing is therefore **not**
   told when the mode later goes `on`; the `/pb` card says where they stand.
5. *"The 400 is about the embed" is decided by asking again without it*, not by reading
   speedrun.com's error text, which no doc describes (§A).
6. *An answer that is JSON but not `{"data": …}` is still an outage* (`BAD_ANSWER`); only `data`
   of the wrong type is the member's own (`MALFORMED`).
7. *The refusals of Look now reuse `pb_feed_failed_said`* with the reason in words; the
   cooldown is a constant. No new key.
8. *A stale claim is settled as a new outcome, `unconfirmed`,* rather than `failed`: Black Bloc
   does not know whether the message went out.

## Review fix 2026-10-07 — the post names the member

Owner, 2026-10-07 ~7:1x AM, verbatim: *"A pb was posted but it didn't say who it belonged to
just a discord user id"*. The feed's first real post (a rehearsal copy in the shadow home) was for
the right member, still in the server. **Cause:** the shipped `pb_feed_post_text` opened with
`{member}`, an @ (`<@id>`) placed inside the embed description; Discord does not reliably resolve a
user mention inside an embed (raw `<@…>` or *@unknown-user* for clients that have not cached the
user, mobile especially). Mentions render reliably only in message content. Fixed on branch
`pb-post-name`:

| What changed | Pinned by |
|---|---|
| Shipped `pb_feed_post_text` = `**{name}** ran **{game}** — {category} in **{time}**{place_line}.` — `{name}` is the server display name escaped by `plain`, the speedrun.com name once they have left. `{member}` stays a field; its help says Discord may show it as a raw id in this post and to use `{name}` | `tests/test_pb_feed.py::test_the_shipped_post_names_the_member_in_words_never_by_an_at`; `tests/test_pb_looks.py` (the rehearsal and `on` posts now read `**Ada** ran …`) |
| New key `pb_feed_post_author` (default `{name}`, fields `{name}` `{runner}`), filed with the other `pb_feed_*` words, because go-live's author line is a key (`golive_live_author`): the embed's author line with `display_avatar.url` when the member is in the server, the speedrun.com name and no icon when not. A blank rendering draws no author line. Registry keys **937 → 938**, core keys 108 → 109 | `::test_the_post_carries_the_members_name_and_avatar_as_its_author`, `::test_a_member_who_left_is_authored_by_their_speedrun_name_with_no_avatar`, `::test_the_author_line_follows_its_own_wording` |
| Markdown in a display name is only ever words: escaped in the body; in the author line it is the name as typed, because Discord renders an author name as literal text (no bold, no masked link, no auto-link) — escaping there would print the backslashes | `::test_markdown_in_a_display_name_is_only_ever_words` (`[free nitro](https://evil.example)`, `**x**`) |
| A staff-stored template using `{member}` keeps working as stored (none was stored live, measured 2026-10-07, so the new default takes effect at deploy) | `::test_a_stored_template_with_member_still_renders_the_mention` (passes before and after — it pins, it was not a failing test) |

A post already made is not touched: no re-render, no new post.

## Gate

Measured 2026-10-05 on branch `pb-feed`, before its docs commit:
`python -m pytest tests -q -p no:cacheprovider -n 8` **11190 passed, 3 skipped** (10911 on `main`);
`python -m ruff check .` clean; `node site/mock/check.mjs` **ok — 25 pages, 312 routes, 141 core
settings, all keys present** (24 / 305 / 101 on `main`); the twelve `site/mock/*.test.mjs` files
exit 0. By import: `len(KEY_TYPES)` **900** (860 + 40), `len(CORE_KEYS)` **141**,
`SCHEMA_VERSION` **89**, `len(COGS)` **29**. The Personal bests page was opened once in a browser
against the local mock: the members list, the mode switch, the filters, the recent posts and the
two folded sections drew, and the console showed no error.

**Review fixes, measured 2026-10-05 on branch `pb-fixes`:** `python -m pytest tests -q -p
no:cacheprovider -n 8` **11413 passed, 3 skipped** (11327 on `main` `c16deab1`); `python -m ruff
check .` clean; `node site/mock/check.mjs` **ok - 25 pages, 312 routes, 150 core settings, all
keys present**; the thirteen `site/mock/*.test.mjs` files exit 0. By import: `len(KEY_TYPES)`
**909** (900 + 9), `len(CORE_KEYS)` **150**, `SCHEMA_VERSION` **89**. The Personal bests page was
opened in a browser against the local mock: the not-posted counts, the staff-set 404 notice and
the *not confirmed* post drew, Block opened its reason dialog, the block landed with the reason
on its log row, and the console showed no error. ⚠️ Another branch is removing keys from the
same registry, so the absolute counts will move at merge; this branch's own delta is **+9**.

## What was NOT verified

- **Review fixes:** no DM has met Discord (fakes only); the nested embed's `400` and the second,
  plain question were never seen from speedrun.com; Unmatch, Clear the opt-out, Set by hand and
  the page with the mode `off` were not pressed in a browser; `docs/info/code-notes.md` was not
  re-keyed and the key counts in other docs were not touched.

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
