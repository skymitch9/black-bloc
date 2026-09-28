# Test audit 2026-09-28 — top-level slice 2 (`test_marathon_near_miss` … `test_youtube_live`)

> **Audience:** the conductor merging the test-audit branches, and any later session asking why a
> test in this slice is shaped the way it is. **Status:** TRACKED. **Last verified: 2026-09-28**
> against branch `test-audit-top2` (base `6dac0fe7`). Measured: full suite 9435 passed (`-n 16`), per-file and slice-wide line
> coverage before/after, the full suite, `ruff check .`. **NOT checked:** the other five slices;
> nothing here was run against Discord, Fly or a browser.

Owner's ask, verbatim: *"Check all unit tests and make sure each is specific and needed. No
redundant, brittle, or unneeded ones"*. Tests only — nothing under `black_bloc/`, `site/`,
`scripts/`, `tests/conftest.py`, `tests/loopback.py` or `tests/fixtures/` was touched.

## Totals

| | Before | After |
|---|---|---|
| Test functions in the slice (45 files) | 1659 | 1600 |
| Collected items in the slice (parametrize ids included) | 2670 | 2679 (more ids: loops and one-input tests became named cases) |
| Slice coverage — lines executed in `black_bloc/` | 27379 of 59125 (46.31%) | 27379 of 59125 (46.31%) |
| Lines executed before and not after (the guard) | — | **0** (and 0 gained) |

Per file the guard was run twice: each changed file alone against its own `6dac0fe7` copy (0 lines
lost in every one), then the whole slice together (above).

Category totals (a test can be merged without being deleted — a merge keeps every case as an id):

| Category | Count | What was done |
|---|---|---|
| Redundant — copy-paste variants merged into one `parametrize` | 72 tests → 15 | every case kept as a named id |
| Redundant — wholly implied by a stronger test, removed | 4 tests + 13 lines | named below |
| Brittle — prose restated from a settings default / module constant | 15 tests | now read from the registry or the constant |
| Unneeded — tests of Python behaviour or of removed code | 3 tests | removed |
| Not specific — a loop that hid which case failed | 2 tests | now parametrize ids |

## Per file

Files not listed were read end to end and left unchanged: `marathon_people`, `marathon_ping`,
`marathon_public`, `marathon_runner_posts`, `marathon_spotlight`, `minutes_audio`,
`minutes_session`, `orphaned`, `panels`, `post_blocks` and `posts` (guard: posts / post_blocks are
owner guarantees — the welcome post as v180 sent it, block limits, exclusive holder, drawn
stamps), `restart`, `rolegrants`, `rolemenu_panels`, `selftest`, `selftest_panels`,
`settings_panel`, `spawned`, `tempvoice` (additive-only pins), `timezones`, `twitch`,
`when_picker`, `youtube_live`.

### `tests/test_settings_store.py` — 220 → 182 functions

| Test(s) | Category | What happened |
|---|---|---|
| 18 `*_panel_minutes` tests (`request`, `poll`, `mod`, `memory`, `youtube`, `pings` (+`voice`), `honeypot`, `settings`, `automod`, `chat`, `raid_train`, `rolemenu`, `birthday`, `event`, `golive`, `modmail`, `test_the_show_panel_goes_quiet…`, `test_the_applications_panel_help_names_the_command…`) | Redundant | One `test_a_panel_stays_up_ten_minutes_by_default_so_discords_window_is_still_open`, 18 ids, same checks for all (default 10, `15` in help, int, reachable, round trip, -1 and `"15"` refused, parse); the five `/x panel` help checks are a column. The two per-key extras stay as `test_the_chat_panel_key_is_picked_up_by_the_prefix_scan_with_no_second_edit` (CHAT_KEYS) and `test_the_event_panel_keys_are_filed_under_events`. |
| 14 decided-bool tests (`settings_core_keys_admin_only` F-S3, `automod_arm_needs_confirm` F-A1, `request_post_buttons`, `request_forum_adopts_posts`, `youtube_unlink_dms_them`, `poll_creator_may_end` I-2, `poll_drafts`, `logs_important_only`, `request_panel_own_list`, `event_panel_own_list`, `birthday_panel_next_for_members` + `_lookup` F-B1, `hide_commands_when_off`, `applications_roster_shows_left`, `applications_panel_own_list`) | Redundant | One `test_a_decided_switch_is_a_bool_key_both_doors_reach_until_a_lead_says_otherwise`, 15 ids named after the owner fork; each keeps its default and its help phrase as columns. |
| `test_golive_channel_defaults_to_live_now…`, `test_the_announce_channel_becomes_live_now…`, `test_the_birthday_channel_defaults_to_the_incumbent_s…`, `test_the_modmail_places_become_the_real_ones…`, `test_the_request_notice_points_nowhere…` | Redundant | One `test_a_place_becomes_the_real_one_once_test_mode_is_off`, 6 ids. TEST_MODE guard: every case kept. |
| `test_a_dashboard_poll_lands_in_the_test_channel…`, `test_the_request_notice_lands_in_the_test_channel…` | Redundant | Folded into `test_defaults_follow_test_mode`, now parametrized (5 ids). |
| `test_the_ping_role_mode_is_read_as_a_feature_switch…`, `test_the_raid_train_mode_is_read_as_a_feature_switch…` | Redundant | One `test_a_feature_mode_is_read_as_a_feature_switch_on_the_health_page`, 2 ids. |
| `test_the_rehearsal_home_help_says_it_widens_test_mode`, `test_the_global_home_says_a_features_own_home_wins` | Redundant | One test: both read the same `KEY_HELP` line. |
| `test_the_youtube_keys_the_panel_only_reads_keep_their_defaults` | Redundant (implied) | All three defaults are pinned by the panel-minutes, decided-bool and live-half tests. |
| `test_the_eight_chat_memory_keys_are_untouched_by_the_panel` | Redundant (implied) | Its eight defaults were `test_every_memory_decision_is_a_key…` line for line; its one extra (help names `/memory`, not `/chat memory`) moved there. |

**Kept, with the guard that kept them:** the key count (`len(KEY_TYPES) == 692` in the banter
test) and the Go-live page's 86; `test_every_registry_key_is_reachable_from_the_panel_as_well_as_the_dashboard`
(every-key guard, checklist 33 — see cross-file below); every `KEY_TYPES` / min / max / refusal test;
the TEST_MODE and shadow-home tests; `test_every_registry_key_the_site_shows_has_a_label`.

### Other files

| File | Before → after | Test | Category | Reason |
|---|---|---|---|---|
| `test_marathon_near_miss.py` | 7 → 6 | `test_an_exact_login_matches_whatever_the_case` + `test_an_exact_schedule_name_matches` → `test_an_exact_login_or_schedule_name_matches` | Redundant | same call, one input each; 2 ids |
| `test_marathon_role.py` | 9 → 9 | `test_a_role_with_any_staff_permission_is_never_handed_out` | Not specific | a loop of five permissions → 5 parametrize ids, so a failure names the permission |
| | | `test_the_block_says_its_shipped_words_and_a_toggle_label` | Brittle | title/label read from `BUTTON_BLOCK_DEFAULTS` |
| `test_marathon_sources.py` | 53 → 54 | the oengus / fastestfurs / ladyarcaders "schedule page and site word" tests | Redundant | site, word and source-set checks → `test_a_non_tracker_source_names_its_site_and_its_word` (3 ids); each source keeps its own schedule-page test |
| `test_marathon_thread_controls.py` | 9 → 7 | four custom-id-template tests (spotlight/off, spotlight/cancel, highlight, ping) | Redundant | one parametrize (4 ids, each action also checked in `ACTIONS`) + `test_the_custom_id_fits_discords_hundred_characters` |
| `test_mentions.py` | 8 → 3 | six one-line mention tests | Redundant | `test_a_mention_reads_as_the_name_a_person_would_type`, 6 ids |
| `test_minutes.py` | 44 → 42 | `…without_the_receive_extension…` + `…without_opus` | Redundant | one refusal parametrize (2 ids; refusal-in-words kept) |
| | | `test_landing_leaves_a_channel_the_guard_allows…` + `test_with_no_guard_at_all…` | Redundant | one parametrize (guard allows / no guard; guard test kept) |
| `test_modcases.py` | 25 → 25 | `test_the_card_row_never_offers_void_and_restore_at_once` | Redundant lines | three `not in` / `len` lines implied by the tuple equality above them |
| `test_modmail.py` | 61 → 59 | `test_the_four_sources_a_reply_can_come_from_are_named_once` | Redundant (implied) | the same tuple is asserted by `test_the_reply_sources_and_the_ticket_sources_are_two_lists_on_purpose` |
| | | `test_the_root_row_one_never_passes_discords_five` | Redundant | its two states joined `test_every_state_fits_inside_discords_five_by_five` |
| | | `test_setup_gains_the_ticket_button…` (renamed from `…and_still_fits_inside_five_a_row`), `test_the_root_leaves_row_nought…` | Redundant lines | their row counting was the five-by-five test again |
| `test_personas.py` | 68 → 67 | `test_a_trope_is_a_value_and_stays_one` | Unneeded | dataclass equality is Python's |
| | | `test_taking_a_side_did_not_loosen…`, `test_the_command_block_is_inside…`, `test_every_mood_block_carries…` | Redundant lines | re-asserted two CORE rules, the cached block and `TONE_CLAUSE` that sibling tests pin |
| `test_pings.py` | 120 → 120 | `test_the_ping_block_says_its_shipped_words…` (+ `…is_drawn_only…`) | Brittle | title/label from `BUTTON_BLOCK_DEFAULTS`; a redundant re-import of `pings` dropped |
| `test_pings_onboarding.py` | 14 → 14 | three tests naming "What should ping you?" / option titles | Brittle | read from `PINGS_ONBOARDING_TITLE`, `BOTH_OPTION`, `RAID_OPTION`, `STREAMER_PROMPT_TITLE` |
| `test_polls.py` | 97 → 92 | five `validate()` refusal tests | Redundant | `test_a_poll_discord_cannot_carry_is_refused_in_words_that_name_why`, 5 ids (refusal-in-words kept) |
| | | `test_a_shadow_note_that_names_something_else…` + `test_a_blank_shadow_note…` | Redundant | one parametrize (checklist-17 id kept) |
| | | `test_the_shadow_note_names_the_channel…` | Brittle | the default read from `polls.SHADOW_NOTE` |
| `test_prefix.py` | 2 → 1 | `test_an_empty_prefix_list_matches_nothing_discord_py_would_look_for` | Unneeded | it tested `str.startswith(tuple())`, which the other test's `== []` already implies |
| `test_presence.py` | 21 → 21 | `test_the_default_bio_carries_the_dashboard_link…` | Brittle | the prose literal went; the template equality and the dashboard link stay |
| `test_preview.py` | 32 → 32 | `test_each_button_block_s_editor_draws…` | Not specific | loop → 4 parametrize ids |
| | | marathon-role block, live-now empty line, Links title, sample link labels | Brittle | read from `BUTTON_BLOCK_DEFAULTS`, `BLOCKS_LIVE_DEFAULTS`, `link_buttons.SAMPLE_ROWS` |
| `test_raidtrain.py` | 65 → 65 | `test_a_member_sees_only_the_move_that_is_theirs_to_make` | Redundant line | its `slots_held` line is `test_the_cap_counts…` again |
| `test_requests.py` | 88 → 87 | `test_a_stored_due_date_stays_a_plain_date_and_never_becomes_an_instant` | Redundant (implied) | `parse_due("2026-09-15") == "2026-09-15"` is the first due-date test's first line |
| | | `test_a_move_into_hold_or_declined…`, `test_the_site_link_is_one_button…` | Redundant lines | OPEN→IN_PROGRESS and empty-origin `site_view` pinned by neighbours |
| | | `test_the_filed_answer_reads_the_stored_sentence…` | Brittle | reads `REQUEST_FILED`; the owner's words stay pinned in `test_settings_store::test_the_filed_line_is_a_text_key…` |
| `test_rolemenus.py` | 35 → 35 | `test_handing_roles_out_needs_options…` | Redundant line | `POST not in card(picking_on=False)` is `test_post_it_is_absent…` |
| `test_shadow.py` | 28 → 28 | two `note_line` tests | Brittle | expected line built from `shadow.NOTE_DEFAULT` (shadow guard: both kept) |
| `test_spotlight.py` | 59 → 58 | `test_the_reminder_fills_the_five_placeholders…` | Brittle | checks the filled parts, not the `SPOTLIGHT_BUMP_TEMPLATE` sentence |
| | | `test_unreadable_wording_falls_back…` + `test_blank_wording_is_the_default_too` | Redundant | one parametrize comparing with the shipped template's own render |
| `test_youtube.py` | 56 → 55 | `test_the_feed_parser_and_the_upload_wording_are_gone_from_the_module` | Unneeded | `hasattr` checks on code removed 2026-09-18; the registry-side guard (`test_the_seven_upload_keys_are_gone…`) stays |

## Cross-file duplicates for the conductor

- `tests/test_settings_store.py::test_every_registry_key_is_reachable_from_the_panel_as_well_as_the_dashboard`
  is implied by `tests/test_settings_panel.py::test_every_key_lands_in_exactly_one_of_the_twenty_five_groups`
  plus `::test_automod_rules_is_the_only_key_in_the_registry_with_no_editor` (the module it tests is
  `settings_panel`). Both are in this slice; **kept** because the brief protects the settings_store
  every-key tests. If the conductor agrees, the settings_store copy can go.
- No duplicate with a file outside this slice was found. Identical assert lines shared with
  `tests/cogs/**` (presence, pings settings, modcases/automod `applied`) test different layers
  (cog UI vs module) and were left.

## Real bugs found (not fixed)

- `black_bloc/pings_onboarding.py:123` hard-codes the fallback `"What should ping you?"`, a second
  copy of `settings_store.PINGS_ONBOARDING_TITLE` (checklist 15, one fact one home). Not a runtime
  bug today — the two strings agree — but a reworded default would leave the fallback behind.

## Not done

Nothing in the slice was skipped: all 45 files were read. Deliberately conservative in `posts`,
`post_blocks`, `tempvoice`, `shadow` and `settings_store` per the brief's guards.
