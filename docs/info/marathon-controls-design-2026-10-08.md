# Marathon controls, streamlined — Layer A, the Discord side (2026-10-08)

> **Layer B (the site drawer) BUILT 2026-10-08 on branch `marathon-controls-b` (off `main` `b4eee247`), NOT merged,
> NOT deployed — section "Layer B" at the end.**
>
> **Audience:** the conductor, reviewers, Layer B (the site drawer) and the next session touching marathon threads, run
> posts, the People view or the `/event ▸ Marathons…` card. **Status:** TRACKED · 🔨 **BUILT on branch
> `marathon-controls-a` (off `main` `dd567a3e`), NOT merged, NOT deployed.** Registry keys **1089 → 1086**, then
> **1090** after the review fix round (four keys added, below), routes unchanged in number (DELETE answers **410** in
> words and left the contract; the `public_highlight` PATCH field answers in words), log kinds
> `marathon.public_highlight_set` and `marathon.feed_ignored` no longer written or listed. Schema unchanged (the
> `marathons.public_highlight` column stays, unread).
> **Last verified: 2026-10-08 11:3x Phoenix** — by the branch's tests (full suite, ruff, `check.mjs` on a worktree mock
> at `MOCK_PORT=8825`, every `site/mock/*.test.mjs`); the new tests were run against `dd567a3e` and fail there (93).
> ⚠️ **NOT checked:** anything in a real Discord client (the controls, a run post, the People view, the card), the live
> database, a real Restore after a thread Archive; nothing was rendered in a browser. Secret NAMES only (none here).
>
> The spec is [`marathon-controls-review-2026-10-08.md`](marathon-controls-review-2026-10-08.md) as amended by the
> owner's fifteen answers (recorded in `docs/TODO.md`). Owner, 2026-10-08: *"Can we also review all the buttons on a
> marathon any we can drop or adjust or rename to have a more streamline experience"*; on blurbs: *"what if we just
> remove all explaining blurbs, we should be fine without them"*.

## The thread controls, row by row

| Phase | Content (state lines only) | Row 0 | Row 1 |
|---|---|---|---|
| Before / during the show | the spotlight line (`Spotlight: on now until <t:…>` · `starts <t:…>` · `kept on Go-live` · `no channel to spotlight`), the role-ping line | Runner announcements · Host announcements · Ping the marathon role · Spotlight follows the schedule *(not drawn when kept or no channel)* · Marathon event | Marathon tracker ↗ · the one BaF event button |
| After the show (`mt.is_over`) | the same state lines | Marathon tracker ↗ · Archive it | — |

Pinned by `tests/test_marathon_thread_controls.py::test_before_and_during_the_show_row_0_is_the_five_switches_and_row_1_the_link_and_baf`,
`::test_after_the_show_only_the_link_and_archive_it_are_drawn`, and the cog's
`test_track_posts_one_pinned_control_message_right_after_the_opening` (labels, custom ids, rows `[0,0,0,0,0,1,1]`).

## Per decision

| # | Before | After | Writer | Reverse | Keys | Test |
|---|---|---|---|---|---|---|
| D1 | Marathon event + BaF run/host events buttons | Marathon event only; `runs` ids answer `RUNS_GONE` | `set_event_mode` (one half moves) | the same button | retired `marathon_controls_runs_on/off` | `test_a_retired_button_answers_in_words_and_changes_nothing[runs-*]` |
| D2 | follow / yes / no (+ Clear) row | ONE button: `BaF event: no (2 of 55 runs) · say yes`, `yes (named X) · say no`, `not decided (12 of 15 runs) · say yes`, `yes/no (staff) · clear`, `yes/no (answered) · clear` | `set_baf_event`, `clear_answer` | staff → follow; answered → clear; worked out → the other answer (a second press of `say no` after a clear forces no) | retired `marathon_controls_baf_follow/_follow_answer/_clear/_yes/_no`; added `_said_yes/_said_no/_said_unsure/_staff_yes/_staff_no/_answered_yes/_answered_no/_named/_runs` | `test_the_baf_event_is_one_button_carrying_the_reading_and_its_one_reverse`, `test_the_baf_event_button_says_its_reading_and_moves_once_each_way`, `test_a_leads_answer_reads_answered_and_the_button_clears_it` |
| D3 | five spotlight labels, one greyed | `Spotlight follows the schedule: on · turn off` / `off · turn on`; dates move to the state line | `start_spotlight` (on, and on-now in reach; also sets follow when the row is already lit), `turn_off_spotlight` = `cancel_spotlight` at every phase (fix round): `set_spotlight_mode(off)` only — a spotlight this marathon's schedule lit is lifted by that canonical writer, one staff or another marathon set stays up and the state line says *on until … · not following the schedule · stop it on Go-live*; a kept row is refused in words; `stop_spotlight` deleted | the same switch | retired `marathon_controls_spotlight_on/off/kept/none/waiting`; added `_spotlight_follow_on/_off`, `_spotlight_until_line/_starts_line/_kept_line/_none_line`, fix round `_spotlight_running_line`, `marathon_controls_follow_off_running_said` | `test_turn_off_during_the_show_stops_following_and_lifts_only_what_the_schedule_lit`, `test_turn_off_during_the_show_leaves_a_staff_spotlight_running_and_says_so`, `test_turn_off_before_the_show_cancels_the_follow_and_leaves_the_row`, `test_a_kept_spotlight_draws_no_switch_says_so_and_an_old_stop_is_refused` |
| D4 | per-marathon Auto-highlight switch | a run's live highlight follows the person's Runner/Host announcements answer (switch, opt-out, the run's own Announce/Don't announce); the guild gates stay as they were | `auto_highlight` (no column read); host blocks `went_live` | Runner/Host announcements, the run's own answer | retired `marathon_public_highlight_default`, `marathon_public_auto_on_said/_off_said/_same_said`, `marathon_controls_highlight_on/off`; `set_public_highlight` deleted | `test_going_live_posts_the_highlight_at_the_shoutout_while_runner_announcements_is_on`, `test_announce_for_one_run_brings_its_highlight_with_runner_announcements_off`, `test_a_highlight_up_follows_its_run_to_the_end_after_the_switch_goes_off` (checklist 38), `test_the_old_per_marathon_column_is_never_read` |
| D5 | one shape | shaped by phase (table above) | `rendered()` | Restore on the site reverses Archive it | added `marathon_controls_archive` | `test_after_the_show_only_the_tracker_and_archive_it_are_drawn`, `test_archive_it_moves_the_marathon_to_the_archive_and_restore_brings_the_buttons_back` |
| D6 | `marathon_controls_help` blurb | removed; state lines only | — | — | retired `marathon_controls_help` | `test_track_posts…` asserts no "Staff:" |
| D7 | per person: answer + No-@, a state line each | one button a person (`Don't announce {name}` / `Announce {name}` / `{name}: back to the default`), one row of five, menus past five (12 a menu); state lines only for exceptions | `set_run_answer` | the same button | defaults of `marathon_announce_button_run_*` lose "for this run" | `test_each_person_gets_one_button_the_move_their_state_allows`, `test_five_people_fit_as_one_row_of_buttons_and_more_become_one_menu`, `test_the_state_lines_name_only_the_exceptions_and_why`, cog `test_a_runs_post_carries_each_persons_moves_and_says_who_is_announced` (rows `[1, 1]`) |
| D11 | Remove on the card, the feed notice, DELETE | gone; old feed `remove` ids answer `REMOVE_GONE`, DELETE answers **410 `remove_gone`** with the same words (fix round; mock too, `check.mjs` `RETIRED`); Archive it is the one move; an archived marathon is never re-added by a feed | `archive_marathon` (why `staff`) | Restore | retired `marathon_remove_question`, `marathon_removed_said`; `remove_marathon`, `ask_remove`, `ignore_removed` deleted | `test_delete_is_retired_answers_in_words_and_archives_nothing`, `test_pause_it_is_the_marathons_own_move_and_an_old_remove_answers_in_words`, `test_archive_it_is_the_one_move_off_the_list` |
| D12 | 14–15 buttons | People… · Untrack (or Track / Track anyway) · Read it now (active only) · Open the thread · Open on the site · Back; the run and event-mode selects stay | inbox `run_action`, `refresh_marathon` | Track ↔ Untrack | retired `marathon_ping_role_button_on/off` | `test_the_card_is_people_untrack_read_the_links_and_back`, `test_the_card_is_people_the_tracking_move_and_read_it_now_while_active` |
| D13 | Event schedule (Hotfix) on the thread | gone; `overlay` ids answer `OVERLAY_GONE`; the drawer keeps it | `set_switch(OVERLAY)` from the site | the drawer | retired `marathon_controls_overlay_on/off` | `test_a_retired_button_answers_in_words_and_changes_nothing[overlay-*]` |
| D15 | Spotlight / Stop spotlighting, constant labels | `Spotlight their channel…` / `Stop spotlighting their channel`; Unlink and Twitch name only when linked; order Link · Unlink · Twitch · Spotlight · opt-out · @ · this run · Back | unchanged writers | unchanged | added `marathon_people_button_spotlight/_unspotlight/_unlink/_link_near/_twitch/_back` | `test_the_slot_view_reads_link_spotlight_opt_out_at_this_run_back_in_that_order`, `test_every_people_view_label_is_a_settings_key` |

## The blurb sweep (Discord)

Removed (keys kept, defaults trimmed to their state; a staff-edited value stays theirs):

| Key | Old text | Now |
|---|---|---|
| `marathon_controls_help` | *Staff: these buttons set **{marathon}**'s events and its channel's spotlight at once. Each one says what is on now and what a press does.* | retired |
| `chat_channel_notes_intro` | *Pick a channel and say what it is for in one sentence. Black Bloc reads that note in place of the channel's Discord topic whenever it points somebody somewhere. **{count}** channel(s) have a note so far.* | **{count}** channel(s) have a note. |
| `chat_voice_intro` | *Every member hears the cookout voice; the tone is what sits on top of it. The server's setting is **{setting}**, and a pin beats it until staff clear it. **{count}** member(s) listed.* | The server's setting is **{setting}**. **{count}** member(s) listed. |
| `chat_review_intro` | ***{count}** answer(s) may have missed. Pick one to approve what the cheap model suggests, change it, or dismiss it.* | **{count}** answer(s) may have missed. |

Looked at and LEFT (ambiguous or not a blurb — the owner's call): `events_where_hint` and `events.WHERE_JOIN_NOTE`
(member help on the Where picker; the hint is an owner-asked key), `chat_voice_off_note` (state plus how to bring
tones back), the `*_panel_footer` keys of `/structure`, `/pb`, `/bracket` ("this panel timed out — run /x again":
state plus the fix), `poll_shadow_note` / `rehearsal_note` (state), `chat_grounding_note` (model prompt, never shown),
`marathon_channel_ping_help` (a SITE line, Layer B). ⚠️ The sweep was a key-name and phrase grep, not a read of every
panel: constants such as `marathon_inbox.INBOX_WAITING` and `marathon_spotlight.SPOT_SHARED` sit in views that no
longer have a Discord door (below) and were not touched.

## Decisions beyond the brief

- **Archive it on the thread has no confirm** — it is reversible (Restore), and a persistent button cannot open the
  card's ephemeral confirm cheaply. After the archive the controls message keeps its state line and loses its buttons
  (`archived_controls`).
- **The skipped host-highlight log row** (`marathon.host_highlight_skipped`) still writes once a block when hosts are
  off, as before; with Auto-highlight gone it now fires for every host block whose hosts are not announced.
- **The `/event` card keeps its two selects** (a run's moves; the event mode, per D1 "`/event` keeps the decision").
- ~~**Doorless views left in place:** the card's Spotlight…, Schedule… (change link, re-read, rename, post now), Next up…,
  Pair, Pause/Resume, board, Make/Unlink event views and handlers still exist and are tested by opening them directly;
  nothing on Discord reaches them now. Follow-up: delete them, or give the owner a door back.~~ **Deleted in the fix
  round** (views, builders, modals, moves, tests); each function is on the drawer (sheet times, Pause/Resume, board,
  Next, Follow the schedule, link, name, read gap, inbox post, event) or the People view (pairs). None was persistent.
- **D7 "five people per row before a menu"** read as: one row of five buttons; six or more people → menus.
- `marathon_controls_cancelled_said` / `_cannot_wait` defaults lost their "Press Spotlight: start" wording.

## For Layer B (the drawer) — ✅ all done on `marathon-controls-b` (section below)

- ✅ `GET /api/marathons/{id}` no longer carries `public_highlight`; a PATCH of it answers `HIGHLIGHT_GONE` and changes
  nothing — drop the drawer's Auto-highlight row. **Done (B 2).**
- ✅ `DELETE /api/marathons/{id}` answers **410** `remove_gone` with `REMOVE_GONE`'s words (fix round) — drop Remove from
  the bar (D11). **Done (B 2).**
- ✅ Retired keys the site listed: `marathon_public_highlight_default`, `marathon_remove_question`,
  `marathon_removed_said`, `marathon_ping_role_button_on/off` and the seventeen thread-controls keys (mock rows and
  `labels.js` lines already removed here). **Re-checked on B: none is named in `site/` (grep), `check.mjs` all keys
  present.**
- ✅ The slot's person moves now say `Don't announce {name}` / `Announce {name}` / `{name}: back to the default`.
  **The drawer draws them from the API's `move_label` (B 2).**

## Review fix round (2026-10-08)

| # | Finding | Now | Test |
|---|---|---|---|
| 1 | Archive it edited the controls after the thread was archived; the site route and the tick never cleared them | `marathon_archive.archive_held` calls `archived_controls` (buttons cleared, an auto-archived thread opened first) BEFORE `archived_inbox` archives the thread — every door | `test_archive_it_on_the_thread_clears_…`, `test_the_sites_archive_clears_…`, `test_the_automatic_archive_clears_…`, `test_an_already_archived_thread_is_opened_…` |
| 2 | Turn off during the show stopped a staff spotlight | cancel-only (D3 row above) | D3 tests |
| 3 | DELETE answered 200 | 410 in words, bot and mock; out of the contract; `check.mjs` `RETIRED` | `test_delete_is_retired_answers_in_words_and_archives_nothing` |
| 4a | `HOST_EVENTS_GONE` a bare notice | key `marathon_host_events_gone_said`: *BaF host events left this switch: they follow BaF run/host events in the marathon's drawer on the site. Nothing was changed.* | `test_a_retired_button_answers_…[hostevents-*]`, `test_the_host_events_retired_answer_is_a_key` |
| 4b | a `{name}` label past 80 cut the move word | `marathon_announce.named_label` shortens the NAME with … | `test_a_long_name_is_shortened_in_a_button_label_…` |
| 4b | no `ends_at` read as over once started | `mtc.after_show`: only a known end is after the show | `test_no_known_end_is_never_after_the_show`, `test_a_started_marathon_with_no_end_keeps_its_switches` |
| 4c | a staff yes/no left the Leads question's Yes/No live | `note_switch`: an open question's buttons give way to `marathon_baf_event_staff_set_line` (*{who} set it on the BaF event switch: {answer}.*); following again restores them | `test_staff_setting_the_switch_closes_an_open_question_and_follow_reopens_it` |
| 4d | doorless card views | deleted (above) | — |
| 4e | five blurbs | `GROUP_INTRO`, `STREAMERS_INTRO`, raid-train `OFF_LINE_STAFF`, and the *…is how…* sentences of `pings.HIDDEN_SELF` and `pings_onboarding.NO_COMMUNITY` deleted (none was a key); modmail `MEMBER_INTRO` left | one assertion each in the mirrored tests |

Keys **1086 → 1090**: `marathon_controls_spotlight_running_line`, `marathon_controls_follow_off_running_said`,
`marathon_host_events_gone_said`, `marathon_baf_event_staff_set_line`; none retired (the deleted views used no key).
⚠️ NOT checked: any of it in a real Discord client (an edit in a real archived thread, a real 80-character label).

## Layer B — the site drawer (2026-10-08)

> Branch `marathon-controls-b` off `main` `b4eee247` (commits B 1–B 4). **NOT merged, NOT deployed.** Registry keys
> **1090 → 1090** (none added, none retired; `marathon_channel_ping_help`'s DEFAULT changed). Routes unchanged in number;
> three response fields added (below). **Last verified 2026-10-08 ~12:5x Phoenix** by the full suite, ruff, every
> gate node fixture, `scripts/site-gate.ps1 -Port 8836` (check.mjs green), and the drawer rendered in headless Chrome
> on the worktree mock (`MOCK_PORT=8835`, `events.html#marathon-1`) and read back from its DOM and one screenshot at
> 1280 wide. ⚠️ NOT checked: phone width, a press in a real browser (the writes were exercised by `curl` on the mock and
> by the API tests), the live bot, Discord.

The drawer, top to bottom: header (one state line: phase · tracked by · thread ↗ · inbox ↗ · read/next · Marathon
tracker ↗; one facts line: dates · runs/BaF · the thread's spotlight line · source ↗ · feed · event · channel) ·
Spotlight + Pings (the channel's cards, D8 kept) · People · **Settings for this marathon** · the posts line · the bar
**Track/Untrack · Read it now · Archive it · More…**.

| # | The drawer now | Keys / data | Test |
|---|---|---|---|
| D4 | No Auto-highlight row; Runner announcements is the one switch | — | DOM read: no "Auto-highlight" |
| D8 | Owner answered **keep it as is**: the Go-live card and the Pings card stay. The Follow the schedule switch left the block for Settings (D14). `marathon_channel_ping_help` trimmed to a state line | `marathon_channel_ping_help` default → *During events pings while one of its marathons runs.* (fix round SF-5; was *Ping windows: its marathons' schedules.*; key kept; a staff value stays) | — (wording) |
| D9 | A slot: Link to a member… · Link @name · Unlink · Twitch name… · Spotlight their channel… / Stop spotlighting their channel · Opt out of every run on this marathon / Opt back in to this marathon · No @ / @ again · Don't announce / Announce / back to the default — then **Open this run on the tracker ↗** · Shout it now · the run's event link. Mark live / done / upcoming and Make it now gone. Opt-out has no confirm (reversible) | People-view keys via the new `labels` on `GET …/people`; `move_label`s as before; tracker `#marathon-N-run-M` | `marathon-words.test.mjs` *a slot draws the People view's set in its order…*, *the tracker link for one run…*; API `test_the_people_answer_carries_the_people_views_labels_as_the_keys_say_them` |
| D10 | Bar: tracking move · Read it now (while read) · Archive it · More…; More… = Reads from + Change the schedule link… · BaF run/host events · Event schedule (Hotfix) · Airs on · Re-read every · Save · Rename… · Pause/Resume · Post it to the inbox now · Back to the sheet's times | — | *the bar is the tracking move, Read it now while active, Archive it and More…* |
| D11 | No Remove anywhere in the drawer; Archive it is a plain button (Restore reverses it) | — | same test (`!includes('remove')`) |
| D14 | Settings = the thread's switches in its order and words, one button each, a press ~~PATCHes~~ is `POST …/press` (fix round SF-1) at once and the drawer redraws (a refusal is the API's sentence in the drawer's notice); Runner/Host show a `default` pill or `back to the default (on|off)`; the role-ping line under Ping, the event line under Marathon event, the BaF event's day lines under BaF event | new `controls` on `GET /api/marathons/{id}` (`action, to, on, label, ~~patch~~ state` — fix round SF-1) from `drawer_switches` — the thread's own labels; `spotlight_line` (the thread's spotlight key, `{until}`/`{starts}` unfilled) | `test_the_drawer_reads_the_threads_switches_in_order_with_their_words_and_patches`, `test_a_marathon_with_a_channel_carries_the_spotlight_switch_after_the_ping`, `test_the_drawer_reads_the_threads_spotlight_line_with_the_time_left_to_fill`, `test_each_switch_has_the_site_patch_that_makes_the_same_move` (11 cases), *BaF run/host events moves only its half* |

Seen failing first: the 15 new Python cases, 5 new node tests and 1 changed node test (`drawerParts` gained *More…*) fail on `b4eee247` (throwaway worktree).

**Decisions beyond the brief, for the owner/reviewer:**
- The brief said D8 = fold the cards; `docs/TODO.md` records the owner's answer as *"keep it as is"* — the owner's
  answer was followed.
- Switch words come from the thread (`Runner announcements: on · turn off`), as one button each — the D14 mock's
  pills read `on`/`off`; one button that says state and move is the thread's shape and keeps one set of words.
- The whole-marathon opt-out label is the existing key's value (*Opt out of every run on this marathon* / *Opt back in
  to this marathon*), not the review's proposed *Opt out of this marathon* — keys reused, wording unchanged; staff can
  change it on Settings.
- The drawer keeps every switch after the show (the thread shows only tracker + Archive it then): staff final say.
- The Spotlight-their-channel and Stop confirms (with an explaining body) were left as they were — not in this brief;
  candidates for the blurb rule.

### Layer B review fix round (2026-10-08)

> Commits on `marathon-controls-b` after `e2d99237`. **NOT merged, NOT deployed.** Registry keys **1090 → 1091**
> (`marathon_run_event_unlink` added; `marathon_channel_ping_help`'s DEFAULT changed again). Routes **+1**
> (`POST /api/marathons/{id}/press`); `PATCH …` keeps its typed fields and *back to the default*. **Last verified
> 2026-10-08** by ruff, the full suite (`-n 16`), every gate node fixture, every asset `--check`,
> `scripts/site-gate.ps1 -Port 8847` (check.mjs green: 346 routes), and `events.html#marathon-1` rendered in headless
> Chrome on the worktree mock (`MOCK_PORT=8848`) with Runner announcements pressed through `POST /api/marathons/1/press`.
> ⚠️ NOT checked: the live bot, Discord, a real browser by hand, phone width.

| # | Finding | Now | Test |
|---|---|---|---|
| SF-1 | The drawer's *Spotlight follows the schedule: turn on* was `PATCH {spotlight_mode: follow}` → `set_spotlight_mode` → `follow_spotlight` → `plan` (nothing when the feature is off, the marathon paused, or the channel off for marathons), while the thread's button is `start_spotlight` (lights and holds the row in reach; refuses `no_channel`/`no_end`/`cannot_wait` in words) | **One handler, by construction:** `POST /api/marathons/{id}/press` `{action, to}` calls the thread's `press(..., via=VIA_WEBSITE)` for EVERY Settings switch (announcements, host announcements, ping, spotlight follow, marathon event, BaF event). `patch_for` deleted; each control carries `{action, to, on, label, state}`. Pairs outside `mtc.DRAWER_MOVES` (archive, retired actions, `cancel`) are 422 `bad_press` in words before `press` runs; refusals come back with the thread's status and words. Thread answers' `<t:…>` stamps are rewritten into the server's time (`mtc.site_words`). Mock `marathonPress` mirrors `press`/`start_spotlight`/`turn_off_spotlight` incl. the refusals; the contract's `PATCH spotlight_mode` entry became the press entry. *Back to the default* stays a PATCH (`{announcements: null}`) — the thread has no such move, so a `default` press action would be a site-only branch inside the thread's handler | `test_spotlight_turn_on_from_the_drawer_is_the_threads_move[feature_off/paused/after_the_show]` (both doors, same row, same follow, same refusal code and words), `test_a_press_that_is_not_a_drawer_switch_is_refused_in_words` (6), `test_each_drawer_switch_presses_through_the_threads_own_handler`, `test_the_site_presses_only_the_drawers_switches` (16), `test_a_thread_answer_reads_its_discord_stamps_in_the_servers_time_on_the_site`, the press route in both auth parametrisations |
| SF-2 | Two *Unlink* buttons in one slot: the person's pairing and the run's event | New key `marathon_run_event_unlink` *Unlink the event* (mock row, `labels.js`), on the detail's `labels.unlink_event`; `runTools` draws it | `test_a_runs_event_unlink_has_its_own_words_beside_the_persons_unlink`; DOM read shows *Unlink the event* beside *Unlink* |
| SF-3 | `TRACKER_WORD` and `'Archive it'` duplicated `marathon_controls_tracker` / `marathon_controls_archive` | `GET /api/marathons/{id}` (live and archived) carries `labels: {tracker, archive, unlink_event}` (`DRAWER_LABELS` / `stored_labels`, mock and contract too); the header link and bar button draw them | `test_the_drawer_reads_the_threads_tracker_and_archive_words_from_their_keys` |
| SF-4 | Blurbs in the drawer | `LINK_NOTE` keeps sentence 1; `SPOTLIGHT_BODY`/`SPOTLIGHT_SLOT_BODY` lose *Stop spotlighting takes it off again.*; `UNSPOTLIGHT_BODY` → *twitch.tv/{login} comes off the Go-live page; an announcement already out stays as posted.*; `NO_BAF` → *Nobody from BaF is on this schedule yet.* None was a key; moved to `marathon-words.js` so a node test pins them (keys only if a cheap path appears — none today) | node *the drawer's ask bodies and empty line say what happens…* |
| SF-5 | `marathon_channel_ping_help` default | *During events pings while one of its marathons runs.* (bot + mock; a staff value stays) | `test_the_marathon_channel_ping_line_says_when_during_events_pings` |
| NIT | `test_marathons.py` asserted `found[3]["label"]` equal to itself | pins *Marathon event: off · turn on* | same test |
| NIT | `SWITCH_STATES` a second action→field map in JS | gone: `defaultBit` reads `control.state` (`STATE_FIELDS` in the cog, from `marathon_hosts.ANNOUNCE`/`HOST_ANNOUNCE`, the names the PATCH reads) | `test_the_drawer_reads_the_threads_switches_in_order_with_their_words_and_moves` asserts `state`; DOM read shows the `default` pill and *back to the default (on)* |
| NIT | "6 new node tests" | 5 new + 1 changed (above) | — |

Every new Python case and the new node test seen failing on `e2d99237` (throwaway worktree).

**Left as found, for the reviewer:** `PATCH {spotlight_mode}` is still an API path into `set_spotlight_mode` (no page
draws it now); the pairing list's *Unlink* and the marathon event's *Unlink* (Event line) still say just *Unlink* — neither
shares a slot with another Unlink, so not in this round.
