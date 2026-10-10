# Sticky messages — one staff-set note per channel, kept at the bottom

> **Audience:** future Claude sessions, reviewers and the owner. **Status:** TRACKED · 🔨 **BUILT on branch
> `sticky-messages`** (off `main` `1cde5594`), **NOT merged, NOT deployed.** **Last verified: 2026-10-05** against
> that branch by the test suite, `ruff`, the node tests, `site/mock/check.mjs` and one look at the mock's Posts page
> in a browser. ⚠️ **NOT checked:** nothing here has met Discord — no copy was posted, deleted or silenced in a real
> channel, no real Forbidden was seen, the `/sticky` panel was never opened in Discord, and schema 88 has not run on
> the live database. See `## What was NOT verified` at the foot. Secret NAMES only.
>
> **2026-10-05, later:** merged to `main` (`b05e4fe3`), then independently reviewed. The review's findings are fixed
> on branch `sticky-fixes` (off `main` `0d159774`) — see `## Review fixes 2026-10-05`. Where a fix reverses a rule or a
> decision below, the old text is struck and the new one sits beside it. Re-verified the same day by the suite,
> `ruff`, the node tests and `check.mjs`; still nothing has met Discord.

> **2026-10-09 — a post can be the sticky, every copy is pinned, and the move waits for quiet** (branch
> `sticky-board`, off `main` `b87ed763`, NOT merged): `sticky_messages.post_id` (schema 93) — a row with a post posts
> the post and its blocks instead of `text`; `sticky_pin_copies` pins every copy (QuietPins removes the notice);
> `sticky_quiet_seconds` (300) and `sticky_max_buried_minutes` (60) make the move wait for 5 quiet minutes after the
> count, never longer than an hour — **the defaults change the cadence of every existing sticky** (0 quiet = the old
> rule). A post owned by a feature (the leaderboard: points) follows that feature's mode and home. The *As briefed*
> rows below about "the words are the only thing posted" and "Only after BOTH a number of messages AND a minimum gap"
> are amended by it — see [`sticky-board-design.md`](sticky-board-design.md).

## The ask

Owner, 2026-10-05, verbatim, picking from a list of popular bot features: *"Let's build 1, 8, 10"* / *"We'll leave
them in shadow for now"*. **8** = sticky messages: a staff-set note that stays at the bottom of a channel, e.g. *how
to submit a run*.

## As briefed (conductor) and as built

| Rule | How it is built |
|---|---|
| ONE sticky per channel: its words, on or off | Table `sticky_messages`, primary key `(guild_id, channel_id)`. `paused` is the off switch; the words are staff's own stored text and are the only thing posted |
| The bot deletes its previous copy and posts again at the bottom | `sticky_posts.Desk._place`: take the old copy down wherever `posted_channel_id` says it is, then send, then store the new id. Old copy that will not delete → **no** new one (never two copies) |
| Only after BOTH a number of messages AND a minimum gap | `sticky_after_messages` (5, 1–100) counted in memory per channel; `sticky_min_seconds` (30, 5–3600) measured from the stored `posted_at`. Count reached inside the gap → ONE timer per channel waits the remainder out, then posts once |
| Bots do not count | `sticky.counts`: `author.bot`, any webhook, and every system message type are ignored; only `default` and `reply` count (checklist 23) |
| Survives a restart, never two copies | `message_id` + `posted_channel_id` + `posted_at` are on the row. The count is in memory (see Decisions 3) |
| `sticky_mode` off / shadow / on, default **shadow** | Shadow posts nothing in the real channel: the copy goes to `shadow.channel_id(feature="sticky")` (`sticky_shadow_channel_id`, else `shadow_channel_id`, else the guard's channel, else the log channel) under the `rehearsal_note` line naming the real channel. Kinds: `sticky.would_post` |
| Both staff doors | `/sticky` (one command, an ephemeral panel) and a **Sticky messages** section on the Posts page. Both call the same `Desk` moves with `via` |
| Every default a settings key | Six keys, namespace **posts**: `sticky_mode`, `sticky_after_messages`, `sticky_min_seconds`, `sticky_silent`, `sticky_panel_minutes`, `sticky_shadow_channel_id` |
| A deleted channel / lost permission is logged once, in words, never retried forever, never raises | `on_guild_channel_delete` deletes the row and writes ONE `sticky.channel_gone`. ~~Any other failure writes its reason to `trouble` on the row~~ **Reversed 2026-10-05 (review fix 2):** only a PERMANENT answer (a missing channel, a missing permission, Discord's 400/403/404, an error nobody expected) writes `trouble`, drops the channel from the watch list and writes ONE `sticky.post_failed`; that row is not tried again until staff press **Try again** / edit it. An OUTAGE (5xx, 429, a timeout, a connection error) leaves the row running and is tried again — see Review fixes 2 |
| Guard and permissions as other posting features | `guard.allows_channel(target)` before any send (refusal → `sticky.would_post` `reason: test_mode`, once per channel per boot); `permissions_for(guild.me)` for View Channel + Send Messages before deleting anything; `AllowedMentions.none()` on every copy |

## The pieces

| File | What it holds |
|---|---|
| `black_bloc/sticky.py` | The row reads/writes, the pure rules (`counts`, `seconds_left`, `state_of`, `card_buttons`) and every word the panel and the answers use |
| `black_bloc/sticky_posts.py` | `Desk` — one per bot (`desk_of(bot)`): the per-channel lock, the counts, the timers, `_place`, and the staff moves `save` / `pause` / `resume` / `remove` / `set_mode`, plus `settle` and `channel_deleted` |
| `black_bloc/sticky_panel.py` | The `/sticky` panel: list, a sticky's card, the words modal, the remove confirm |
| `black_bloc/cogs/moderation/sticky.py` | Thin: `on_message`, `on_guild_channel_delete`, `on_ready` reconcile, the settings hooks, the slash command |
| `black_bloc/api/tools/sticky.py` | `GET /api/sticky`, `PUT /api/sticky/{channel}`, `POST …/pause`, `POST …/resume`, `DELETE /api/sticky/{channel}` |
| `site/public/assets/sticky-section.js` | The Posts page section, mounted by `page-posts.js` |

### States (one word, read off the row and the mode — `sticky.state_of`)

`stopped` (has `trouble`) · `paused` · `off` (mode off) · `waiting` (running, no copy up) · `live` (copy in its own
channel **and the mode is not shadow** — review fix 4) · `rehearsing` (copy somewhere else, i.e. the rehearsal home,
or any copy at all while the mode is shadow).

### Log kinds (head `sticky` files under **Posts**)

| Kind | Level | When |
|---|---|---|
| `sticky.set` / `sticky.edited` / `sticky.paused` / `sticky.resumed` / `sticky.removed` / `sticky.mode` (+ `web.` for the first five) | routine | The staff move, one row each (checklist 34: the route passes `via`, never notes a second row) |
| `sticky.posted` | routine | A copy placed by a staff move, a mode change or the boot reconcile — **not** by people talking (Decisions 4) |
| `sticky.would_post` | routine (shadow) | The same moment in shadow, with `rehearsed`, `shadow_home`, `message_id`; or `reason: test_mode` when the guard refused |
| `sticky.post_failed` | important | Once per stop, with the sentence that is also on the row. Also once per OUTAGE, with `retrying: true` and a reason that says Discord could not be reached (review fix 2) — the same kind on purpose, so no new kind had to be registered |
| `sticky.channel_gone` | important | Once, when Discord deletes the channel |

## Decisions made beyond the brief

1. **A section of the Posts page, not a page of its own** (`posts.html#sect-sticky`). The `/settings` group select
   holds 25 groups and the registry already has 25, so a `sticky` namespace was not available; the keys are filed
   under **posts** through `NAMESPACE_OVERRIDE`, and the site's precedent for a small feature that shares a
   namespace is a section on that namespace's page (the front door on Modmail, spotlights on Go-live). Its log rows
   file under Posts for the same reason (`logkinds.HEADS["sticky"] = "posts"`), so the panel's **Logs** button and the
   Posts page's Logs fold show them; there is no `sticky_log_level` — `posts_log_level` governs.
2. **`sticky_silent`, default on.** A copy is sent with Discord's silent flag so moving it to the bottom does not
   light up notifications. A key, so staff can turn it off.
3. **The message count is in memory.** A restart resets it to zero, so the next move needs `sticky_after_messages`
   new messages after the boot. The alternative was a database write for every message in every sticky channel.
   What survives is what the brief named: the copy's id and where it is.
4. **A move caused by people talking writes no log row.** It bumps `reposts` on the row (shown as *moved N×* on the
   panel and the page) instead. A busy channel moves its sticky every 30 seconds; a row each time would be thousands
   a day and would bury the Posts log. Placements staff or the bot's own reconcile cause ARE logged
   (`sticky.posted` / `sticky.would_post`). ⚠️ If the owner wants every move in the log, it is one `log_action` in
   `Desk._place`.
5. **In shadow the rehearsal copy moves exactly as the real one would** — deleted and posted again in the rehearsal
   home on the same count and gap — so the cadence can be watched before the flip. One rehearsal copy per sticky.
6. **Pause takes the copy down** and keeps the words; **Resume** posts at once. **Mode off** takes every copy down
   and keeps every row. A mode change, or a change to `sticky_shadow_channel_id` / `shadow_channel_id` /
   `log_channel_id` (the last added 2026-10-05: it is the rehearsal home of last resort), moves the copies at once
   through a settings hook (`Desk.settle`) rather than waiting for the next message. ⚠️ The guard's test channel is
   the third fallback and is NOT a setting, so it has no hook; it only changes with a restart, which settles anyway.
7. **A stopped sticky stays stopped.** `trouble` is cleared only by **Try again** (the resume move), an edit, or a
   pause. Nothing retries on a clock, which is what *not retried forever* was read to mean. **Narrowed 2026-10-05
   (review fix 2):** *stopped* now means Discord gave a permanent answer. An outage never stops a row, and a row
   stopped ONLY because the rehearsal home was unset or missing is started again by `settle` once a home resolves.
   Still nothing on a clock: an outage is retried by the next person's message, no sooner than `sticky_min_seconds`.
8. **Reversal does not depend on the mode** (checklist 3): take-down reads `posted_channel_id` off the row, so a
   copy posted under `on` is removed after a flip to `shadow` or `off`, and Remove works in every mode.
9. **No loop.** Checklist 25 asks for a loop beside any startup-only reconcile; nothing here ages on a clock — every
   transition has a trigger (a message, a staff move, a settings hook, `on_ready`, the channel-delete event). A copy
   a moderator deletes by hand is simply posted again at the next move. `on_ready` runs under `loops.Reconciler` and
   every placement re-reads the row inside the channel's lock (checklist 37).
10. **Text and announcement channels only**; 1800 characters, leaving room under Discord's 2000 for the rehearsal
    note. Threads and forum posts are not offered.
11. **The panel's own labels are constants in `black_bloc/sticky.py`**, as on `/honeypot`. Nothing the bot POSTS in
    a channel is a constant: a copy is staff's stored words, plus `rehearsal_note` in shadow. ⚠️ Candidate follow-up
    under the every-word-editable rule if the owner counts ephemeral panel labels.
12. **`/sticky` hides while the mode is off** (`HIDDEN_WHEN_OFF`), like every other feature; the ways back are
    `/settings` and the Settings / Posts pages. The mode is also a picker on the panel.
13. ~~**`page-posts.js` no longer reads a `#sect-…` hash as a post slug**~~ **Reversed 2026-10-05:** that rule made a
    post titled *Sect rules* (slug `sect-rules`) impossible to open. Only the page's four section ids
    (`posts-hash.js:SECTION_HASHES`) are sections now; every other hash is a post. `posts.html#sect-sticky` still
    opens the section, and the bot's **Open on the site** button still uses that link. A post whose slug is exactly
    one of the four ids loses to the section — accepted, there is no way to tell them apart from the hash.
14. **The mock's `KIND_HEADS` gained `post` / `posts` / `sticky` → posts**, mirroring `logkinds.HEADS`; before this
    the mock filed post rows under Core.
15. **`tests/api/conftest.py`'s `WebChannel` gained `get_partial_message`** — the take-down uses the one-call
    partial delete, and the fake had only `fetch_message`.

## Review fixes 2026-10-05

An independent review of the merged build. Every row: what was wrong, what changed, the test that pins it. All tests
are in the mirror files (`tests/test_sticky_posts.py` unless a path is given) and each was run against the unfixed
`main` `0d159774` in a throwaway worktree and seen to fail there; the two exceptions are named under the table.

| # | Finding | What changed | Pinned by |
|---|---|---|---|
| 1 | `off` / `shadow` left a real-channel copy up when the row was stopped or paused: `settle` skipped every row that was not running before it looked at the copy | `Desk._settle_one` asks `_misplaced` FIRST: a stored copy that is not where `_wanted` puts it (nowhere when the mode is off or the row is paused; its own channel under on; the rehearsal home under shadow) is taken down whatever `paused` / `trouble` say. Only then does it stop at a row that is not running (checklist 38: the guard gates the start of an effect, not the clean-up of one in flight) | `test_a_stopped_stickys_copy_comes_down_when_the_mode_leaves_on[off/shadow]`, `test_a_paused_sticky_whose_copy_would_not_delete_loses_it_at_the_next_settle[off/shadow/on]` |
| 2a | One 503, timeout or dropped connection stopped a sticky for good | `sticky_posts.passing(exc)`: 5xx, 429, `TimeoutError`, `OSError` (every connection error), `aiohttp.ClientError`. `Desk._failed` sends those to `_unreachable`: no `trouble`, the row stays running and watched, ONE `sticky.post_failed` per outage (`retrying: true`, *Discord could not be reached (it answered 503)…* — never *refused*, never a permission). While the outage lasts the very next person's message retries (not the Nth), no sooner than `sticky_min_seconds` after the failed try (`Desk._wait`, `Desk.tried`); the first success clears it. `trouble` is left for 400/403/404 and the unexpected | `test_an_outage_leaves_it_running_says_so_once_and_the_next_message_retries[unavailable/TimeoutError/ConnectionResetError]`, `test_an_outage_is_retried_no_sooner_than_the_gap`, `test_a_copy_that_times_out_on_delete_is_kept_on_the_row_and_tried_again`, `test_only_an_outage_that_passes_by_itself_is_retried` |
| 2b | A deleted or unset rehearsal home stopped every sticky and setting a home did not bring them back | `sticky.is_home_trouble` recognises the two home sentences (`TROUBLE_NO_HOME`, `TROUBLE_HOME_GONE`) by their own wording — no new column. `settle` clears such a `trouble` when the target now resolves (a home was set, or the mode left shadow) and places the copy. Any other stop is untouched | `test_a_sticky_stopped_for_a_missing_home_comes_back_when_one_is_set`, `test_a_sticky_stopped_for_no_home_at_all_comes_back_too_and_no_other_stop_does` |
| 2c | The delete path's sentence was doubled (*The last copy could not be deleted — It could not be posted — TimeoutError: . Press Try again. — so…*) | `_take_down` returns the exception, not a finished sentence; `sticky_posts.why(exc)` is the bare reason (*Discord refused (403): Missing Permissions*, *RuntimeError*, *RuntimeError: no*) and `TROUBLE_OLD_COPY` wraps it once | `test_an_old_copy_that_will_not_delete_says_one_sentence_not_two[…]` |
| 3 | Pause said *taken down* while the copy was still up; Remove deleted the row and orphaned the message; in shadow the pause answer named the real channel | Pause answers one of three sentences off what happened: `PAUSED_NOW` naming where the copy WAS (`posted_channel_id`, so the rehearsal home in shadow), `PAUSED_NO_COPY`, or `PAUSED_COPY_LEFT` — still in which channel, why, a link to the message, and the two ways out. **Remove still removes** (see Decisions below) and answers `REMOVED_COPY_LEFT` with the same three facts; both log rows carry `copy_left`, `left_channel_id`, `left_message_id` | `test_pause_says_the_copy_is_still_up_when_discord_would_not_delete_it`, `test_remove_names_the_copy_it_could_not_delete_with_a_link`, `test_a_pause_in_shadow_names_the_rehearsal_home_the_copy_was_in`, `test_a_pause_with_no_copy_up_does_not_claim_to_have_taken_one_down` |
| 4 | A rehearsal home equal to the sticky's own channel posted in that real channel during shadow, and the state read `live` | `Desk._target` returns no channel and no reason for that case and `_place` goes to `_own_home`: any copy there comes down, nothing is posted, ONE `sticky.would_post` `reason: own_home` per channel per boot, and the answer is `SAVED_OWN_HOME`. The row is `waiting`, not stopped. `state_of` never answers `live` while the mode is shadow | `test_a_rehearsal_home_that_is_the_stickys_own_channel_gets_no_copy_in_shadow`, `test_a_live_copy_comes_down_when_shadow_makes_its_own_channel_the_home`, `tests/test_sticky.py::test_the_state_word_is_read_off_the_row_and_the_mode` (two new rows) |
| 5 | A store that failed after a successful send left a copy the row did not know, so the next move posted a second | `_place` wraps the store: on ANY failure (a cancelled task included) `_unsend` deletes the message just sent, best effort, and the error is raised on. The row then says *no copy* and that is true. If the delete fails too there is nothing left to try: one warning names the channel and the message id | `test_a_copy_sent_but_not_stored_is_deleted_so_the_next_one_is_the_only_one` (fault injected into `rules.write_copy`) |
| s1 | Rehearsal note + words could pass 2000 characters (a 400, which stopped the row) | `sticky.fit(note, words)`: the NOTE is cut with `…` to the room left; the words staff wrote are never cut, and with no room at all the note is dropped | `test_a_long_rehearsal_note_is_cut_and_the_staff_words_never_are` |
| s2 | Six messages at once made six timers, one tracked | `Desk.deciding`: a channel being decided on (the row read between the check and the timer) is skipped by every other message, so there is one tracked timer per channel | `test_six_messages_at_once_make_one_tracked_timer` |
| s3 | The API stored `"['a', 'b']"` for `{"text": ["a","b"]}` | `Desk.save` refuses anything but a string (`NOT_WORDS`, `bad_text`, 400) — in the shared move, so both doors | `test_words_that_are_not_a_string_are_refused_in_words[…]`, `tests/api/tools/test_sticky.py::test_words_that_are_not_a_string_are_refused_and_nothing_is_stored[…]` |
| s4 | A post whose slug starts `sect-` could not be opened | Decision 13, reversed above. `site/public/assets/posts-hash.js:postSlugOf` | `site/mock/posts-hash.test.mjs` (in CI) |
| s5 | The Posts page showed `<#333>` and backticked key names in `trouble` and in answers | `api/tools/sticky.py:site_words` — the API answers the page in site-safe words: `<#id>` → `#name` (or *a channel Discord no longer has (id)*), backticks dropped; `**bold**` stays, the page's `notice` draws it. Applied to `trouble`, every answer and every refusal. The stored `trouble` and the Discord panel keep the mention | `tests/api/tools/test_sticky.py::test_the_page_is_answered_in_channel_names_never_discord_markup` |
| s6 | The mock refused every channel type but `text` | `STICKY_POSTABLE = ['text', 'news']` in `site/mock/server.mjs`, the same list as `sticky.POSTABLE_KINDS`. The mock also gained the non-string refusal, the own-home case, the three pause answers and the `#name` wording, so its answers read as the API's do | `check.mjs`; ⚠️ no fixture — the mock has no announcement channel to save into |
| s7 | Changing `log_channel_id` while it was the fallback home did not move the copies | `log_channel_id` joined `MOVES_THE_COPIES` (Decision 6) | `tests/cogs/moderation/test_sticky.py::test_moving_the_log_channel_moves_a_copy_that_rehearses_in_it` |

**Seen failing before the fix, with two caveats.** `test_only_an_outage_that_passes_by_itself_is_retried` tests a
function that did not exist, so it could only fail by absence. `test_a_long_rehearsal_note_…` failed on the missing
constant before reaching its length assertion; the old body was `note + "\n" + words` = 387 + 1 + 1800 = 2188
characters for that fixture, which is arithmetic, not an observed failure of that line.

### Decisions the fixes made

1. **Remove removes, and names what it left** — it does not refuse. A refusal would trap staff: a bot that can no
   longer SEE the channel gets a 403 on the delete for ever, never a 404, so the row could never be removed (the
   staff-final-say rule). The leftover is not lost: the answer carries the channel, the reason and a link to the
   message, and the `sticky.removed` log row carries `left_channel_id` / `left_message_id`.
2. **Pause pauses even when the copy stays up**, and says so. The copy comes down at the next `settle` (a boot, or a
   change to the mode or a home key) or by **Resume** then **Pause** once the cause is fixed.
3. **An outage is counted in memory** (`Desk.outage`, `Desk.tried`). A restart forgets it, so a long outage that spans
   a restart writes one more `sticky.post_failed`. The alternative was a column, and `storage/db.py` was out of scope.
4. **A rate limit (429) is an outage**, not a refusal; discord.py normally waits those out itself.
5. **The home-trouble match is by wording** (`HOME_TROUBLES`, built from the two templates). ⚠️ Rewording either
   sentence keeps working for new rows but leaves rows stopped under the OLD wording un-revivable by `settle`; staff
   still have **Try again**.
6. **Site-safe words are made in the API**, not on the page: no page had a helper for this (`polls.py` still answers
   `<#id>`), and the API is the one place that has the guild to name a channel from.
7. **`site/public/assets/posts-hash.js` is a new file**, not a hunk of `page-posts.js`, because `page-posts.js` mounts a
   page at import and cannot be loaded by a node test.

## Merge notes for the conductor

- Schema **87 → 88** (new table only, `CREATE TABLE IF NOT EXISTS`, no backfill). Registry **779 → 785**. Two sibling
  builds were cut from the same `main`; each will also claim 88 and move the key count, so the version, the count
  assertion (`tests/test_settings_store.py`), `tests/storage/test_db.py` and `site/mock/contract.json`'s
  `settings.min` / `settings.max` blocks need re-measuring at merge.
- Cogs 26 → 27. Staff commands 17 → 18. `HIDDEN_WHEN_OFF` 17 → 18. `check.mjs`: 23 pages, **300** routes (was 295).
- `docs/info/code-notes.md` gained one section keyed by NAME; re-key after the merge as usual.

## What was NOT verified

- **Nothing met Discord.** No copy posted, deleted or sent silently; the silent flag's effect on notifications, the
  channel select's type filter, the modal and the confirm card were exercised through fakes only.
- **Discord's rate limits** for a delete + send every 5 seconds (the floor of `sticky_min_seconds`) — reasoned, not
  measured. The default is 30.
- **`guild.me` permissions on the live server's channels** — not read.
- **Schema 88 on the live database** — the migration is a new table and ran only on test databases.
- **The site section in a browser** was looked at once on the mock (rows, the three states, search, the deep link);
  the Add and Edit dialogs, Pause/Resume/Remove and the mode switch were NOT clicked in a browser — they are covered
  by `check.mjs` at the route level only.
- **TEST_MODE with a rehearsal home that differs from the guard's channel** — one test, fakes.
- **The review fixes (2026-10-05)** — fakes only, like everything above. Not seen for real: a 503 or a timeout from
  Discord, what status a delete answers when the bot cannot see the channel, the message link opening the right
  message, and the Posts page in a browser after the wording change (the mock's answers were read from the API by a
  script, not looked at on the page).
