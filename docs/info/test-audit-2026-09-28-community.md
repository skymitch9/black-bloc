# Test audit 2026-09-28: `tests/cogs/community/`

> **Audience:** the owner (who asked on 2026-09-28: *"Check all unit tests and make sure each is
> specific and needed. No redundant, brittle, or unneeded ones"*) and any session merging the
> `test-audit-*` branches. **Status:** TRACKED. **Last verified: 2026-09-28**, on branch
> `test-audit-community` off `origin/main` at `6dac0fe7`. Measured that day: the slice's pytest
> count, the coverage diff, the full suite (`pytest -q -n 16`) and `ruff check .`.
> ⚠️ **NOT checked:** the fake-class preambles at the top of each file (lines ~1–500 of the large
> files) were not read line by line for dead fake methods. The pinned sections (`test_pinned_*`,
> the v180 welcome test, the boot double-post and lock tests) were only skimmed, because the brief
> protects them. No other slice was touched.

One slice of six. The siblings audit the other slices on their own branches, so this file covers
`tests/cogs/community/test_*.py` and nothing else.

## Result

| Measure | Before | After |
|---|---:|---|
| Test ids collected (slice) | 1389 | **1386** |
| Test functions (slice) | 1209 | **1184** (−25) |
| Executed `black_bloc` lines, slice-only coverage run | 27510 | **27511**. **0 lines lost** in every source file. One gained: `events.py` `_reconcile_broke`, which is now run instead of having a private attribute checked. |
| Full suite `pytest -q -n 16` | — | **9423 passed, 0 failed** |
| `ruff check .` | — | **All checks passed** |

The coverage guard: `coverage run --source=black_bloc -m pytest -p no:randomly tests/cogs/community`
went to `before.json` and `after.json`, both kept outside git. A script then compared the executed
line set of every source file. The first after-run lost `events.py:2735-2736`
(`wanted_event_id`), so the test that reaches it was put back (see events below). The final diff
lost nothing.

**Category totals** (a test counts once for each change made to it): **redundant 24 · brittle 33 ·
unneeded 4 · not specific 20.** No real bugs were found.

## Per file

| File | Ids before → after | Functions before → after |
|---|---|---|
| `test_applications.py` | 84 → 85 | 80 → 79 |
| `test_birthdays.py` | 104 → 106 | 102 → 100 |
| `test_events.py` | 342 → 342 | 331 → 325 |
| `test_frontdoor.py` | 99 → 97 | 96 → 94 |
| `test_live_blocks.py` | 4 → 4 | 4 → 4 (no change) |
| `test_minutes.py` | 22 → 22 | 22 → 21 |
| `test_polls.py` | 202 → 200 | 192 → 190 |
| `test_posts.py` | 33 → 33 | 33 → 33 |
| `test_requests.py` | 158 → 157 | 138 → 135 |
| `test_role_menus.py` | 137 → 137 | 136 → 134 |
| `test_tempvoice.py` | 204 → 203 | 175 → 169 |

A merge into `@pytest.mark.parametrize` can leave the id count the same or even raise it while the
function count falls. That is the intended trade: each case keeps its own id, and a failure names
the case.

### `test_applications.py`

| Test | Category | Change |
|---|---|---|
| `test_submitting_stores_the_answers_with_their_labels_and_cards_them` | not specific | `card_channel_id == STAFF or == TEST` became `== STAFF_CHANNEL`, because the fixture has no guard. |
| `test_approving_on_a_list_form_hands_nothing_over_and_still_tells_them` | not specific | `any(...) or member.dms` was true for any DM. It now asserts the approved DM names **Stream Team**. |
| `test_somebody_taken_off_a_list_can_be_put_back_on_it` | not specific | An either-or on `said` became `said == REINSTATED_SAID.format(...)`. |
| `test_an_approved_role_form_offers_nothing_and_a_stranger_offers_nothing_either` | redundant | Folded into `test_every_status_renders_exactly_its_row_of_the_button_table` as two ids of the same table. |
| `test_the_settings_sub_panel_writes_every_value_it_shows` → `…shows_each_value_beside_its_select` | not specific | The old name promised writes. The test only checks what is shown. |
| `test_the_logs_button_answers_a_new_message_and_still_refuses_a_stranger` → `test_the_logs_button_refuses_a_stranger_in_words` | not specific | The old name promised an answer. The test only checks the refusal. |

### `test_birthdays.py`

| Test | Category | Change |
|---|---|---|
| `test_the_sweep_posts_once_on_the_day_and_never_twice`, `test_only_todays_rows_are_picked`, `test_posting_today_by_hand_wishes_the_unsent_and_leaves_the_sent` | brittle | The literal `"Happy Birthday **PT**!"` is now `BIRTHDAY_TEMPLATE.format(name="PT")`, the registry default. `0x4EEFFF` is now `DEFAULT_COLOR_VALUE`. |
| `test_the_command_answers_ephemerally_with_a_panel` | brittle | The colour literal is now `DEFAULT_COLOR_VALUE`. |
| `test_the_view_disables_every_item_and_says_so_on_timeout` | brittle | The footer literal is now `PANEL_TIMEOUT_FOOTER`. The test name is referenced in the docs, so it was kept. |
| `test_off_does_nothing_at_all` + `test_an_unavailable_server_is_left_alone` | redundant | Now one parametrized test, `test_the_sweep_touches_nothing_while_off_or_while_the_server_is_unavailable[mode-off / server-unavailable]`. Checklist 32 (skip an unavailable guild) is still pinned by its own id. |
| `test_the_group_and_its_twelve_subcommands_are_gone` → `test_birthday_is_one_command_and_not_a_group` | unneeded | The `hasattr` list of 13 retired method names tested code that no longer exists. `test_pinned_birthday_is_the_cog_s_only_command` already pins the command list. The `isinstance(Command)` check was kept. |
| `test_the_birthday_command_is_a_panel_and_not_a_group` | redundant, removed | It was wholly implied by the `isinstance(Command)` check above. |
| `test_the_modal_takes_every_separator_and_both_shapes` | not specific | The loop became a parametrize (`slash / dot / space / with-a-year`). |
| `test_the_counts_used_by_status` → `test_stored_counts_split_self_from_imported_and_count_only_the_opted_in` | not specific | The new name says what the counts are. |
| `test_a_loop_that_stops_is_recorded_and_started_again` | not specific | The name promised a restart. The test now asserts `restart()` is called (checklist 28). |
| `test_birthdays_rehearse_in_their_own_home_over_the_global_one` | not specific | `"#" in said` became `"#log" in said`. |

### `test_events.py`

| Test | Category | Change |
|---|---|---|
| `test_a_duration_black_bloc_cannot_read_is_refused` | redundant, removed | Its body was identical to `test_submit_re_checks_rather_than_trusting_the_button_that_rendered_it`, which is named in the docs and was kept. |
| `test_the_review_channel_is_the_staff_s_to_delete_by_hand` + `test_with_the_reach_key_off_the_review_channel_is_as_it_was` | redundant | Now one test, `test_the_staff_reach_key_decides_whether_staff_may_delete_the_review_channel[reach-key-on… / reach-key-off…]`. |
| `test_a_number_nobody_proposed_is_read_as_nothing` → `test_a_typed_event_number_is_read_with_or_without_its_hash` | not specific (kept) | This fact is also pinned in `tests/test_events.py`, the mirror file. Deleting it here cost 2 lines of slice coverage, so the coverage guard kept it and only the name changed. The `" 12 "` whitespace case appears nowhere else. |
| `test_both_loops_carry_their_own_error_handler` | brittle, removed | It asserted the private `_error` attribute. It was replaced by running both handlers: `test_a_loop_that_raises_records_the_error_and_restarts_itself[golive / reconcile]`. |
| `test_in_test_mode_the_card_channel_is_recorded_beside_the_message` + `test_the_card_channel_is_the_review_channel_when_the_guard_is_off` | redundant | Now one test, `test_the_card_channel_is_recorded_beside_the_message_and_is_the_review_room[test-mode / guard-off]`. |
| `test_settings_can_forget_the_category_and_the_announce_channel` → `test_an_empty_category_select_forgets_the_category` | redundant half | The announce half repeated `test_an_empty_channel_select_clears_the_key_it_owns`. |
| `test_the_staff_select_caps_at_25_and_says_how_many_are_left` | brittle | The placeholder literal is now `panels.CAPPED_PLACEHOLDER.format(...)`. |
| `test_a_replaced_panel_never_edits_the_render_that_replaced_it` | not specific | An either-or became the single branch that is true. |
| `test_the_where_button_label_carries_the_channel_by_name` + `…a_typed_place_too` | redundant | Now one test, `test_the_where_button_label_carries_what_was_picked[a-channel-by-name / a-typed-place]`. |
| `test_a_channel_and_a_link_are_both_stored_on_the_row` + `test_a_channel_where_is_stored_as_a_channel_not_as_text` | redundant | Now one test, `test_a_channel_where_is_stored_as_a_channel_with_its_link_beside_it[…]`. |
| `test_the_draft_never_gets_the_open_link_button_because_it_would_come_and_go` | not specific | The loop became a parametrize (`half-filled / ready-to-submit`). |
| `test_refuse_answers_in_words_and_leaves_the_draft_where_it_was` | not specific | `count("\n") == 0 or …` became `said == WHERE_REFUSED_MISSING.format(url=…)`. |
| `test_in_test_mode_a_room_goes_after_the_minutes_key…`, `test_with_no_guard_the_days_key_is_what_counts…`, `test_the_room_carries_a_delete_message_under_the_card`, `test_the_delete_message_counts_in_minutes_while_the_guard_is_on` | brittle | The literals `5` and `7` now come from the settings store (`EVENTS_TEST_RETENTION_KEY`, `events_channel_retention_days`). |
| `test_a_post_somebody_deletes_by_hand_cancels_the_event` | not specific | `… or member.dms` became a check that the DM carries the `review_channel_deleted` sentence. |
| `test_the_old_room_is_told_where_it_went_before_it_goes` | brittle | The literal of a settings-key default is now `EVENTS_MOVED_LINE.format(post=…)`. |
| `test_the_upcoming_block_lists_approved_events_only_while_events_are_on` | unneeded | Local imports that repeated module-level ones were dropped. |

### `test_frontdoor.py`

| Test | Category | Change |
|---|---|---|
| `test_a_message_id_is_stored_as_text_because_a_snowflake_is_not_a_js_number` | redundant, removed | `test_posting_the_door_stores_both_keys_and_leaves_one_routine_line` already asserts `store.get(FRONTDOOR_MESSAGE) == str(id)`, and an int could not pass that. |
| `test_a_blank_front_door_home_follows_the_global_one` | redundant, removed | It had the same setup as `test_shadow_posts_the_copy_in_the_rehearsal_home_and_nothing_in_the_real_channel`, which asserts strictly more. |
| `test_a_channel_test_mode_refuses_is_rehearsed_in_the_home_instead`, `test_shadow_posts_the_copy_in_the_rehearsal_home…`, `test_in_shadow_the_one_message_goes_to_the_posts_rehearsal_home` | brittle | The rehearsal-note literal is now `shadow.NOTE_DEFAULT.format(channel="#welcome")`, from the `rehearsal_note` key. |

### `test_minutes.py`

| Test | Category | Change |
|---|---|---|
| `test_the_same_words_somewhere_else_are_ignored` + `test_the_bots_own_message_never_stops_a_meeting` | redundant | Now one test, `test_stop_notes_is_ignored_unless_a_person_says_it_in_the_meetings_chat[said-in-another-channel / said-by-the-bot-itself]`. |

### `test_polls.py`

| Test | Category | Change |
|---|---|---|
| `test_a_message_id_finds_the_poll_it_belongs_to` | redundant, removed | The gateway-vote tests already cover both branches of `poll_for_message` (found and ignored). |
| `test_with_the_mode_on_a_real_channel_is_still_refused_under_test_mode` | redundant, removed | Its body was the same as `test_test_mode_refuses_a_poll_outside_the_test_channel`, which asserts more. The test-mode guard is still pinned. |
| `test_the_settings_command_shows_the_switches_and_the_loop_health` | brittle | `60 minute(s)` now comes from `poll_reminder_minutes`. |
| `test_a_number_the_registry_would_not_take_is_refused_in_words` | brittle | `== 24` became "unchanged from before the submit". |
| `test_the_settings_embed_says_where_drafts_stand` | brittle | `14 day(s)` now comes from `poll_draft_days`. |
| `test_the_pick_select_caps_at_25_and_says_how_many_are_left` | brittle | The placeholder is now `CAPPED_PLACEHOLDER`. |
| `test_forgetting_a_deleted_dashboard_channel` → `test_a_deleted_poll_channel_is_forgotten_and_falls_back_to_the_default` | not specific | The new name says the behaviour. |
| `test_the_logs_button_still_refuses_a_demoted_staffer_in_words` → `test_the_logs_button_refuses_a_member_in_words` | not specific | The test uses a member who never held staff. |

### `test_posts.py`

| Test | Category | Change |
|---|---|---|
| `test_the_panel_writes_a_line_per_post_and_offers_the_way_in`, `test_an_empty_panel_says_so_rather_than_showing_nothing` | brittle | Label and placeholder literals now use `NEW_POST`, `LOGS`, `SITE_BUTTON`, `MODE_PICK` and `PICK_A_POST`. |
| `test_the_panel_says_where_shadow_puts_it_and_the_select_shows_the_third_value` | brittle | The option labels now come from `MODE_OPTION.format(mode=…)`. |
| `test_the_card_says_where_a_shadow_press_would_actually_go` | brittle | The prose literal is now `posts.SHADOW_LINE.format(...)`. |
| `test_the_card_offers_add_a_block_and_a_remove_for_each_block_it_has` | brittle | An 8-item literal list that restated the registry is now derived from `post_blocks.KINDS` minus the block the post already has. |

### `test_requests.py`

| Test | Category | Change |
|---|---|---|
| `test_the_same_staffer_may_not_accept_their_own_review_once_the_server_says_so` | redundant, removed | Same setup as `test_accept_is_not_rendered_when_the_server_asks_for_a_second_pair_of_eyes`. Its only extra assert, that the status is unchanged, cannot fail when nothing is pressed. |
| `test_a_member_with_nothing_filed_is_told_so_when_the_list_is_on` + `…is_told_nothing_by_default` | redundant | Now one test, `test_a_member_with_nothing_filed_is_told_so_only_when_the_list_is_on[list-on / list-off-by-default]`. |
| `test_the_timeout_footer_falls_back_to_the_message_when_no_token_was_recorded` + `…when_the_token_has_expired` | redundant | Now one test, `…falls_back_to_the_message_without_a_live_token[no-token-recorded / token-expired]`. |
| `test_the_staff_select_caps_at_25_and_says_how_many_are_left` | brittle | The placeholder is now `CAPPED_PLACEHOLDER`. |
| `test_the_review_row_puts_the_site_link_on_a_second_row` | brittle | `len(...) == 8` became the exact list it counted, built from `EXPECTED_BUTTONS`, `HANDOFF_BUTTONS` and `SITE_BUTTON`. |
| `test_the_logs_button_still_refuses_a_demoted_staffer_in_words` → `test_the_logs_button_refuses_a_member_in_words` | not specific | The test uses a member, not a demoted staffer. |

### `test_role_menus.py`

| Test | Category | Change |
|---|---|---|
| `test_role_diff_only_touches_menu_roles` + `…ignores_selections_outside_the_menu` + `…empty_selection_removes_everything_the_menu_owns` | redundant | Now one table, `test_role_diff_moves_only_the_roles_the_menu_owns[3 ids]`. |
| `test_an_update_leaves_the_columns_it_was_not_given` | unneeded line | `assert UNSET is not None` was dropped. |
| `test_the_request_buttons_survive_a_restart_by_their_custom_id` | unneeded lines | Two `issubclass(..., discord.ui.Modal)` asserts were dropped. They tested the class hierarchy, not behaviour. |
| `test_a_click_after_the_database_goes_away_answers_a_sentence` | not specific | `"database" in … or "unavailable" in …` became `== DB_UNAVAILABLE`. |

### `test_tempvoice.py`

| Test | Category | Change |
|---|---|---|
| `test_the_panel_is_persistent_and_keyed_by_action` | redundant, removed | Same ids and the same persistence check as `test_pinned_the_in_channel_controls_keep_every_custom_id`, which the blocks-convert build protects. |
| `test_lock_and_unlock_can_be_asked_for_by_name` | redundant, removed | `test_voice_lock_and_unlock_call_the_same_helper_the_button_does` drives the same `do_privacy` both ways and asserts more. |
| `test_a_banned_member_loses_sight_of_the_channel_too` | redundant, removed | `test_banning_someone_denies_connect_and_moves_them_out` asserts `{"connect": False, "view_channel": False}`. |
| `test_the_creator_spot_falls_back_to_the_named_afk_channel` + `…to_the_bottom` | redundant | Now one test, `test_the_creator_spot_falls_back_without_a_set_afk_channel[…]`. |
| `test_a_room_starts_from_the_lobby_s_own_permissions_not_the_category_s` + `test_the_category_setting_puts_a_room_back_on_the_category_s_permissions` | redundant | Now one test, `test_a_room_starts_from_the_permissions_the_room_source_setting_names[…]`. |
| `test_the_block_draws_nothing_with_the_mode_off` + `…while_temp_voice_is_in_shadow` | redundant | Now one test, `test_the_block_draws_nothing_unless_temp_voice_is_on[mode-off / in-shadow]`. This is the lobby block, not a `test_pinned_*` test. |
| `test_the_bitrate_modal_bounds_what_the_range_used_to` | not specific | The loop became a parametrize (`zero / too-high / negative`). |
| `test_in_shadow_a_room_is_hidden_from_members_even_though_the_allowed_role_may_join` | not specific | The `if allowed is not None:` assert was made unconditional. It could have silently checked nothing. |
| six tests on the setup, repair and staff block (for example `test_setup_puts_the_creator_in_the_test_category…` and `test_the_panel_says_how_to_get_a_channel_when_you_have_none`) | brittle | The literal `"join to create a channel"` is now `TEMPVOICE_CREATOR_NAME`, the `tempvoice_creator_name` default. |
| `test_a_reconcile_loop_that_stopped_records_the_error_and_restarts_itself` | brittle line | The private `_loop._error` assert was dropped. The restart itself is still asserted. |

## Considered and kept

| Test | Why it stayed |
|---|---|
| Every `test_pinned_*` test (birthdays, events, frontdoor, tempvoice) | Additive-only pins from blocks-buttons, blocks-convert and birthday-block-modal. |
| `test_the_welcome_post_carried_as_a_block_goes_out_exactly_as_v180_sent_it` | The owner guarantee "exactly as v180 sent it". It overlaps `test_a_carrying_post_goes_out_as_one_message_with_the_door_last`, which is the post-carries-door test and checks different fields. |
| Boot double-post and lock tests: frontdoor `test_two_reconciles_at_boot_*`, `test_a_door_already_up_twice…`, `test_the_duplicate_row_names_both_ids…`, `test_the_live_cadence_waits_for_the_one_reconcile_lock`; events `test_two_reconciles_at_boot_forget_a_gone_room_once`, `test_every_gone_room_at_boot…`; `test_on_ready_does_not_reconcile_again…` in both files | Reconciler and lock pins, checklist 37. Two of them share a setup on purpose. |
| `test_the_buttons_are_registered_by_template…` (asserts the `DECIDE_TEMPLATE` literal), events `test_the_review_view_is_persistent…` (`event:9:approve`), role_menus `test_the_request_buttons_survive_a_restart…` (`rolereq:12:approve`), `test_custom_id_round_trip` (`rolemenu:12`) | These look like restated literals, but they are **persisted custom-ids** on messages already posted in Discord. Changing one strands live buttons. |
| `test_the_poll_loop_runs_often_enough_to_be_a_last_call` (`POLL_MINUTES == 5`), `test_the_loop_ticks_every_minute…` (live_blocks) | Cadence decisions, pinned on purpose. |
| role_menus `test_seed_data_is_well_formed` (`== 6`) and `test_every_sentence_about_the_seed_counts_the_menus_correctly` (source scan for "five"/"six") | These pin a wording bug in which the sentences miscounted the seed. Brittle by design, and cheap. |
| `test_the_mock_servers_copy_of_the_refusal_has_not_drifted` | Named in `code-notes.md` as a drift guard. |
| role_menus `test_taking_roles_back_renders_only_when_they_hold_one` | `test-suite-profile.md` §3.2 row 8 judged it not redundant with the helper test. |
| role_menus `test_a_staff_assign_still_lands_while_the_mode_is_off` vs `test_the_staff_select_still_hands_a_role_over_while_role_menus_are_off` | Both carry the §C6 owner reversal. The first alone proves the **grant** is written while the mode is off. |
| requests `test_the_first_pair_of_eyes_may_still_ask_the_requester` | It shares a setup with the accept-not-rendered test, but its point, that Ask stays available, is its own. |
| polls `test_flipping_shadow_to_on_leaves_an_open_rehearsal_where_it_is` | A shadow test. Today no code runs between its two lines, but it pins that nothing starts to. |
| tempvoice `test_every_view_and_modal_answers_its_own_errors` (`issubclass(…, AnswersErrors)`) | Checklist 8 and 30. The mixin is our own code, not a library's. |
| tempvoice `TEMPVOICE_CREATOR_NAME == made.name` | The lobby is recognised **by name** (`lobbies_by_name`), so the name is behaviour. |
| requests `test_a_view_with_no_message_yet_does_nothing_on_timeout` | Listed in `test-suite-profile.md` §5 as assertion-less. It now has two assertions. |
| Every "refused in words" test, every shadow or TEST_MODE guard test, every key-editable test | Protected by the brief. Where two such tests overlapped exactly (polls test mode, frontdoor blank home), one was kept and it still pins the guard. |

## Real bugs found

None. No test exposed a defect in `black_bloc/`.

One gap for the `tests/test_events.py` slice owner: `wanted_event_id(" 12 ")` (surrounding
whitespace) is tested only in `tests/cogs/community/test_events.py`. If the mirror file adds that
case, the cog-level copy becomes removable.

## Not done

- The fake-class preambles (roughly the first 200–560 lines of each large file) were not audited for
  unused fake methods. A scan found no unused top-level helpers, fixtures or constants.
- The birthdays block section and the frontdoor carries-door and blocks sections were read but
  scarcely touched, because the brief protects them.
- Short button labels such as `"Post it"` and `"Take it down"` still appear as literals. The brief
  targets prose that comes from settings keys, and churning every short label was judged not worth
  the diff.
