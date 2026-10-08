# Marathon controls, streamlined — Layer A, the Discord side (2026-10-08)

> **Audience:** the conductor, reviewers, Layer B (the site drawer) and the next session touching marathon threads, run
> posts, the People view or the `/event ▸ Marathons…` card. **Status:** TRACKED · 🔨 **BUILT on branch
> `marathon-controls-a` (off `main` `dd567a3e`), NOT merged, NOT deployed.** Registry keys **1089 → 1086**, routes
> unchanged in number (DELETE and the `public_highlight` PATCH field answer in words), log kinds
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
| D3 | five spotlight labels, one greyed | `Spotlight follows the schedule: on · turn off` / `off · turn on`; dates move to the state line | `start_spotlight` (on, and on-now in reach; also sets follow when the row is already lit), `turn_off_spotlight` (= `cancel_spotlight` before the show, `stop_spotlight` while held by this marathon or in reach) | the same switch | retired `marathon_controls_spotlight_on/off/kept/none/waiting`; added `_spotlight_follow_on/_off`, `_spotlight_until_line/_starts_line/_kept_line/_none_line` | `test_turn_off_during_the_show_stops_it_as_staff_off_does`, `test_turn_off_before_the_show_cancels_the_follow_and_leaves_the_row`, `test_a_kept_spotlight_draws_no_switch_says_so_and_an_old_stop_is_refused` |
| D4 | per-marathon Auto-highlight switch | a run's live highlight follows the person's Runner/Host announcements answer (switch, opt-out, the run's own Announce/Don't announce); the guild gates stay as they were | `auto_highlight` (no column read); host blocks `went_live` | Runner/Host announcements, the run's own answer | retired `marathon_public_highlight_default`, `marathon_public_auto_on_said/_off_said/_same_said`, `marathon_controls_highlight_on/off`; `set_public_highlight` deleted | `test_going_live_posts_the_highlight_at_the_shoutout_while_runner_announcements_is_on`, `test_announce_for_one_run_brings_its_highlight_with_runner_announcements_off`, `test_a_highlight_up_follows_its_run_to_the_end_after_the_switch_goes_off` (checklist 38), `test_the_old_per_marathon_column_is_never_read` |
| D5 | one shape | shaped by phase (table above) | `rendered()` | Restore on the site reverses Archive it | added `marathon_controls_archive` | `test_after_the_show_only_the_tracker_and_archive_it_are_drawn`, `test_archive_it_moves_the_marathon_to_the_archive_and_restore_brings_the_buttons_back` |
| D6 | `marathon_controls_help` blurb | removed; state lines only | — | — | retired `marathon_controls_help` | `test_track_posts…` asserts no "Staff:" |
| D7 | per person: answer + No-@, a state line each | one button a person (`Don't announce {name}` / `Announce {name}` / `{name}: back to the default`), one row of five, menus past five (12 a menu); state lines only for exceptions | `set_run_answer` | the same button | defaults of `marathon_announce_button_run_*` lose "for this run" | `test_each_person_gets_one_button_the_move_their_state_allows`, `test_five_people_fit_as_one_row_of_buttons_and_more_become_one_menu`, `test_the_state_lines_name_only_the_exceptions_and_why`, cog `test_a_runs_post_carries_each_persons_moves_and_says_who_is_announced` (rows `[1, 1]`) |
| D11 | Remove on the card, the feed notice, DELETE | gone; old feed `remove` ids and DELETE answer `REMOVE_GONE`; Archive it is the one move; an archived marathon is never re-added by a feed | `archive_marathon` (why `staff`) | Restore | retired `marathon_remove_question`, `marathon_removed_said`; `remove_marathon`, `ask_remove`, `ignore_removed` deleted | `test_delete_is_retired_answers_in_words_and_archives_nothing`, `test_pause_it_is_the_marathons_own_move_and_an_old_remove_answers_in_words`, `test_archive_it_is_the_one_move_off_the_list` |
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
- **Doorless views left in place:** the card's Spotlight…, Schedule… (change link, re-read, rename, post now), Next up…,
  Pair, Pause/Resume, board, Make/Unlink event views and handlers still exist and are tested by opening them directly;
  nothing on Discord reaches them now. Follow-up: delete them, or give the owner a door back.
- **D7 "five people per row before a menu"** read as: one row of five buttons; six or more people → menus.
- `marathon_controls_cancelled_said` / `_cannot_wait` defaults lost their "Press Spotlight: start" wording.

## For Layer B (the drawer)

- `GET /api/marathons/{id}` no longer carries `public_highlight`; a PATCH of it answers `HIGHLIGHT_GONE` and changes
  nothing — drop the drawer's Auto-highlight row (`marathons-section.js` ~line 1001/1026 still reads it).
- `DELETE /api/marathons/{id}` answers `REMOVE_GONE` (200, `removed: false`) — drop Remove from the bar (D11).
- Retired keys the site listed: `marathon_public_highlight_default`, `marathon_remove_question`,
  `marathon_removed_said`, `marathon_ping_role_button_on/off` and the seventeen thread-controls keys (mock rows and
  `labels.js` lines already removed here).
- The slot's person moves now say `Don't announce {name}` / `Announce {name}` / `{name}: back to the default`.
