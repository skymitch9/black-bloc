# Test audit 2026-09-28 — `tests/cogs/content/`

> Audience: whoever merges the test-audit branches and any later session touching these tests.
> Status: TRACKED. Last verified: **2026-09-28**. The slice and the full suite were both run
> (`pytest -q -n 16`: 9418 passed, 0 failed), `ruff check .` came back clean, and coverage was
> diffed line by line. NOT checked: whether the `path:line` keys in `code-notes.md` for
> `tests/cogs/content/test_golive.py` still line up. Lines moved, so re-key them at the merge
> under the standing rule.

Owner ask (2026-09-28): *"Check all unit tests and make sure each is specific and needed. No
redundant, brittle, or unneeded ones."* Branch `test-audit-content`, tests only.

## Method

1. An AST scan looked for test bodies with the same structure (constants normalised). A
   pairwise similarity pass (≥0.86) then ran inside each file. Every hit was read by hand.
2. Every test name in the 22 files was read. The files were grepped for registry-length counts,
   `sleep`, tests with no assert, private-attribute asserts, and asserts that restate a
   `settings_store.py` default string.
3. Coverage guard: `coverage run --source=black_bloc -m pytest -p no:randomly tests/cogs/content`
   ran before and after. For each file, the executed lines after must include every line
   executed before.

## Result

| | Before | After |
|---|---|---|
| Tests in the slice | 1346 | 1338 |
| Executed `black_bloc` lines (slice run) | 30587 | 30587, **0 lines lost** |
| Full suite | not run | 9418 passed, 0 failed |

Category totals:

- **Redundant: 13 tests.** 8 were removed. 5 were folded into parametrized tests, which did not
  change the count.
- **Brittle: 5.**
- **Unneeded: 2.**
- **Not specific: 1.**

**No real bugs found.**

## Per file

| File | Before → after | Change |
|---|---|---|
| `test_marathon_feeds.py` | 71 → 71 | Redundant: `test_the_seed_gives_the_ss4c_channel_row_an_oengus_feed_once`, `…_fastestfurs_channel_row_its_feed_once` and `…_lady_arcaders_row_its_feed_once` were one body with three inputs. They are now `test_the_seed_gives_the_channel_row_its_feed_once[oengus-ss4c/fastestfurs/ladyarcaders]`. |
| `test_marathon_near_miss.py` | 11 → 10 | Redundant: `test_the_buttons_outlive_a_restart` (a membership check) is implied by `test_pinned_the_marathon_cog_registers_its_eight_buttons_before_the_role_block`. Brittle: the post sentence and three button labels were restated prose. They are now rendered from `MARATHON_NEAR_MISS_POST_KEY`, `_HERE_`, `_EVERYWHERE_` and `_NOT_KEY`. The allowed-mentions check (names the member, never pings) stays. |
| `test_marathon_public.py` | 19 → 18 | Redundant: `test_the_button_outlives_a_restart` is implied by the pinned eight-buttons test in the same file. |
| `test_marathon_inbox.py` | 36 → 35 | Redundant: `test_the_inbox_buttons_outlive_a_restart`, same reason. |
| `test_marathon_thread_controls.py` | 33 → 32 | Redundant: `test_the_buttons_outlive_a_restart`, same reason. Redundant: `test_the_ping_button_is_staff_only` copied `test_the_buttons_are_staff_only_and_rebuild_from_their_custom_id` with a different action. They are now one test parametrized `[events-button, ping-button]`, and the ping case also gains the custom-id rebuild check. |
| `test_youtube.py` | 115 → 114 | Not specific and redundant: `test_linking_says_out_loud_that_live_announcements_are_off` only asserted `"off" in sent`. It is merged with `test_linking_never_claims_anything_was_counted_as_seen` into `test_linking_says_announcements_are_off_and_never_claims_anything_was_seen`, which pins `LIVE_MODE_OFF_NOTE` itself. Redundant: `test_logs_still_refuses_a_staffer_who_was_demoted_since_the_panel_opened` joined the existing `test_a_staffer_demoted_while_the_panel_is_open_moves_nothing` parametrize (`[logs, link-for]`). |
| `test_raidtrain.py` | 111 → 110 | Unneeded: `test_the_test_channel_constants_are_still_what_the_fakes_expect` asserted the test file's own constants and ran no bot code. |
| `test_spotlight.py` | 167 → 166 | Unneeded: `test_the_cog_and_the_golive_cog_are_two_different_things` compared two class names. Redundant: `test_a_move_on_a_row_that_has_gone_says_so_rather_than_crashing` and `…_rather_than_a_bare_status` are now `test_a_move_on_a_row_that_has_gone_says_so_in_words[remove/give_role]`. Redundant: `test_the_add_modal_refuses_a_backwards_range_and_adds_nothing` and `…_refuses_an_unreadable_date_by_name` are now `test_the_add_modal_refuses_a_bad_date_in_words_and_adds_nothing[backwards-range/unreadable-date-named]`. |
| `test_golive.py` | 201 → 200 | Redundant: `test_presence_enrichment_fills_a_missing_game` made the same call as `test_a_twitch_presence_is_still_enriched`. Its one extra assert (the title) moved into that test. Redundant: the three status-line end-wording tests are now `test_the_status_lines_quote_what_the_end_wording_does[appends/rewrites/blank]`. |
| `test_marathon.py` | 88 → 88 | Redundant: `test_a_near_marathon_is_read_every_poll_gap_and_a_far_one_is_not` and `test_a_far_marathon_waits_the_far_gap` are now `test_a_marathon_is_read_again_only_once_its_gap_is_up[near-poll-gap/far-gap]`. The old name promised a far case that the test never ran. |
| `test_chat.py` | 131 → 131 | Brittle: `test_a_number_outside_its_range_names_the_field_and_the_range` asserted the cap stayed `20`, which restates the registry default. It now compares with the value read before submit. Brittle: `test_a_failed_reply_leaves_no_cooldown_and_no_action_row` and `test_a_bare_hello_gets_a_toned_wave_instead_of_a_sentence` read the private `cog._answered`. Both now send a second ping and check it: after a failed reply the retry IS answered, and after a wave the follow-up is NOT. This pins the code-notes `chat.py:137` guarantee through behaviour. `test_the_cog_seeds_the_code_tables_the_first_time_it_loads` lost its `cog._seeded` line, because the next test already covers seeding once. |
| the other 11 files | unchanged | Read; nothing worth changing. |

## Considered and KEPT

| Test | Why kept |
|---|---|
| `test_every_notice_item_outlives_a_restart` (feeds) | Named for KI-20. The eight-buttons pin implies it, but it is a named incident guard. |
| `test_pinned_the_marathon_cog_registers_its_eight_buttons_before_the_role_block` (public) | Owner pin (blocks-buttons, code-notes `marathon.py:1578`). Left in place rather than moved to `test_marathon.py`. |
| `test_the_button_is_registered_by_the_marathon_cog_so_it_outlives_a_restart` (role) | Pins a different fact: the role button is registered LAST. |
| `test_the_cog_has_no_uploads_sweep_left_on_it` (youtube) | Removal guard from `youtube-uploads-removal-design.md`. |
| golive `_end_tasks == {}` asserts (grace and flap tests) | Code-notes pins. Without a sleep, this is the only proof that no end task leaks. |
| chat role-ping tests for staff, members and DMs (similar bodies) | Each is a separate security path under the owner's mention rules. |
| chat and pings "bad number" vs "out of range" pairs in the limits modal | Two refusal paths with different words (the refusals-in-words guard). |
| chat_memory "every click re-asks the DB" vs "modal button refuses" | Different paths: one edits the panel, the other opens a modal. |
| every `*_is_refused_in_words`, shadow/TEST_MODE guard, Reconciler lock, replay/spotlight timing and key-count test | Hard guards of this audit. |
| thread-controls button labels written as literals (`"Spotlight: off · start"` …) | Short labels that read as state names. `test_the_help_line_and_labels_are_keys_and_an_edit_re_renders` and `test_the_ping_labels_are_keys` already prove they are keys. A later pass could read them from the registry. |

## Not done

- The five 1.5k–3.3k-line files did not get a line-by-line read of every test body. The
  structural scan, the similarity scan and a read of every name covered them. Pairs below 0.86
  similarity were not read.
- The `code-notes.md` keys into `tests/cogs/content/test_golive.py` were not re-keyed, because
  docs are out of scope for this branch.
