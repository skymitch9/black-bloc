# Test audit 2026-09-28 — moderation, storage, live, scripts, api (top level)

> **Audience:** whoever merges branch `test-audit-modstore`, and any later session asking why a
> test in this slice was removed, merged or kept. **Status:** TRACKED. **Last verified: 2026-09-28**
> — measured on branch `test-audit-modstore` off `origin/main` `6dac0fe7`: slice pytest, full
> suite (`-n 16`), `ruff check .`, and a line-level coverage diff. ⚠️ **NOT verified:** `tests/live/`
> was audited by reading only (no credentials were supplied, by design); nothing was run against
> Discord or the deployed host.

Owner's ask (2026-09-28): *"Check all unit tests and make sure each is specific and needed. No
redundant, brittle, or unneeded ones."* Slice: `tests/cogs/moderation/`, `tests/storage/`,
`tests/live/`, `tests/scripts/`, `tests/api/test_*.py` (not `tests/api/tools/`).

## Result

| Measure | Before | After |
|---|---|---|
| Slice tests collected (default run, `live` deselected) | 1085 | 1079 |
| `tests/live/` tests collected (`-m live`, skipped without env) | 74 | 74 |
| Full suite `pytest -q -n 16` | — | 9420 passed, 0 failed |
| `ruff check .` | — | All checks passed |
| `black_bloc` lines executed by the slice | 32354 | 32354 |
| Lines executed before and not after (any file) | — | **0** |

Coverage guard: `coverage run --source=black_bloc` over the slice (`-p no:randomly`),
`coverage json`, then a per-file set difference of `executed_lines` (before minus after). Empty
for every file.

**Totals by category:** redundant 9 (5 removed as implied by / identical to another test, their
asserts folded in where they added anything; 4 copy-paste pairs merged into parametrizes);
brittle 8 rewritten; unneeded 1 removed; not specific 3 renamed. **Real bugs found: none.**

## Per file

### `tests/api/test_assets.py` — 7 → 7

| Test | Category | Change |
|---|---|---|
| `test_the_build_id_changes_when_an_asset_changes` + `..._is_added` | redundant | merged → `test_the_build_id_changes_when_the_assets_do[an-asset-changes / an-asset-is-added]` (identical bodies, one input differed) |

### `tests/api/test_server.py` — 31 → 30

| Test | Category | Change |
|---|---|---|
| `test_health_stays_public` | redundant | removed — wholly implied by `test_health` (same request, no cookie, asserts 200 and more) |
| `test_health` | not specific | renamed `test_health_answers_without_a_session`, carrying what the removed test said |
| `test_every_page_asks_for_the_favicon_this_app_can_actually_serve` | brittle | `len(pages) >= 13` restated the page count; now `assert pages` (the per-page loop is the point) |

### `tests/api/test_sessions.py` — 12 → 12

| Test | Category | Change |
|---|---|---|
| `test_the_cache_cannot_grow_without_bound` | brittle | read `cache._seen`; now asserts through `get()` that exactly the newest 10 of 25 survive |

### `tests/api/test_auth.py` — 59 → 59

| Test | Category | Change |
|---|---|---|
| `test_a_flood_of_spoofed_keys_evicts_the_oldest_not_the_one_in_use` | brittle | asserted only the private dict, and its second flood evicted the in-use key too, so it never proved its own name. Now: the key in use survives one eviction (`take` still refuses it) and the oldest spoofed key comes back fresh. Would fail under plain FIFO eviction. |
| `test_the_bucket_refills_and_cannot_grow_without_bound` | brittle | the bound half read `bucket._seen`; now pins the exact bound through `take()` (key 500 survives, key 499 is gone) |

Kept (auth guard): every other test, including `test_a_reader_route_costs_the_operator_one_token_not_two`,
which still reads `_seen` — the token balance has no public readout without clock injection, and
the test pins a double-charge bug.

### `tests/api/test_selftest_api.py` — 10 → 10

| Test | Category | Change |
|---|---|---|
| `test_the_list_is_capped_so_one_page_never_grows_without_bound` | brittle | was `assert RUNS_LIMIT == 20` (a constant equal to itself); now sets the cap to 1, runs twice, and the list shows one run |

### `tests/api/test_settings_api.py` — 30 → 30

| Test | Category | Change |
|---|---|---|
| `test_a_multi_enum_round_trips_and_comes_back_in_the_registrys_own_order` | brittle | the eight-item `choices` literal is now `KEY_CHOICES["request_channel_moves"]` |

### `tests/api/test_status.py` — 49 → 48

| Test | Category | Change |
|---|---|---|
| `test_the_retired_go_live_end_switch_is_not_a_feature_because_it_is_not_a_key` | unneeded | asserted a retired key is absent from `KEY_TYPES`; `mode_keys()` derives from `KEY_TYPES`, so the status half was implied and the registry half pins code that no longer exists |

Kept: `test_every_mode_key_in_the_registry_is_reported` (its `>=` set is the owner-facing
feature list) and the poll-review exclusion (pins `NOT_A_FEATURE`).

### `test_bot_api.py`, `test_contract.py`, `test_costs.py`, `test_names.py`, `test_ref.py`, `test_writes.py` — unchanged

Kept: every access/refusal test (auth guard); `test_the_read_bucket_lives_in_auth_and_writes_re_exports_the_same_one`
(one-fact-one-home guard); `test_reader_dependency_still_charges_a_signed_in_staffer` (`_seen`
is the only readout, as above); the contract file's registry/mock mirror tests (each names the
drift it caught).

### `tests/scripts/test_sync_personality_pool.py` — 7 → 7

| Test | Category | Change |
|---|---|---|
| `test_the_shipped_script_exits_non_zero_while_the_canonical_does_not_exist` | brittle | ran `"python"` from PATH (whatever interpreter that is); now `sys.executable` |

### `tests/storage/test_db.py` — 94 → 94, unchanged

Kept, every one: all schema-upgrade tests (the only proof old files still upgrade; the two
structurally identical pairs — vote_scheme/keep_minutes and schema 71/72 — upgrade DIFFERENT
tables and versions, so they are not duplicates); every uniqueness/CHECK constraint test
(checklist 6 — the database half of the lock). `assert SCHEMA_VERSION == 79` in
`test_connect_bootstraps_schema` looks like a restated constant but is **kept on purpose**:
`docs/info/architecture.md` and `docs/info/blackmail-threads-design.md` name
`tests/storage/test_db.py:16` as one of the two lines that carry the schema number, so a bump
must touch it deliberately.

### `tests/cogs/moderation/test_honeypot.py` — 73 → 72

| Test | Category | Change |
|---|---|---|
| `test_setup_is_staff_only` | redundant | removed — the identical call (open the panel as a non-staffer) as `test_the_panel_is_staff_only_and_says_so_in_words`; its asserts (no view, no channel made) moved into that test |
| `test_the_settings_card_says_how_to_get_the_command_back_when_the_mode_is_off` | not specific | built the card twice and never set the mode its name claimed; one build, renamed `test_the_settings_card_says_where_the_settings_live_and_offers_numbers_and_back` |
| `test_staff_and_bots_are_ignored_and_their_posts_are_left_alone` | not specific | only ever posted as a bot; renamed `test_a_bot_in_the_trap_is_logged_exempt_and_carded_only_at_log_level_all` (the staff case is `test_a_staff_role_is_exempt_because_it_can_see_the_staff_channel`) |

### `tests/cogs/moderation/test_modcmds.py` — 48 → 45

| Test | Category | Change |
|---|---|---|
| `test_a_timeout_that_worked_tells_the_member_how_long_it_is` | redundant | repeated the first call of `test_timeout_reads_the_duration_and_clamps_at_twenty_eight_days`; its DM assert moved there |
| `test_the_logs_button_refuses_somebody_who_is_not_staff` | redundant | press for press the `[Logs]` case of `test_a_staffer_demoted_mid_panel_moves_nothing_the_reads_included` |
| `test_role_grants_refuses_a_member_in_words_and_draws_nothing` | redundant | press for press the `[Role grants…]` case of the same parametrize |
| `test_a_staffer_demoted_mid_panel_moves_nothing_the_reads_included` | — | gained the removed tests' asserts (no embed, no modal), so nothing they checked is lost |

### `tests/cogs/moderation/test_modmail.py` — 220 → 220

| Test | Category | Change |
|---|---|---|
| `test_naming_a_ticket_that_is_not_a_number_is_refused` + `test_a_ticket_number_written_in_exotic_digits_is_refused` | redundant | one parametrize, ids `a-word` / `an-exotic-digit-isdigit-accepts` (the second is the regression: `"²".isdigit()` is true, `int("²")` raises) |
| `test_the_ticket_channel_is_the_staff_s_to_delete_by_hand` + `test_with_the_reach_key_off_the_ticket_channel_is_as_it_was` | redundant | one parametrize over `STAFF_REACH_KEY` on/off |
| `test_a_refused_send_is_a_log_row_and_the_ticket_opens_anyway` + `test_no_transcripts_channel_is_a_log_row_not_a_raise` | redundant | one parametrize, `test_an_open_card_that_cannot_land_is_a_log_row_and_the_ticket_opens_anyway[discord-refuses-the-send / no-transcripts-channel]` |
| `test_a_refusal_is_sent_once_per_member_until_the_cooldown_is_over` | brittle | cleared the cog's private `_refused` dict; now moves the module clock past `REFUSAL_COOLDOWN_MINUTES` |

Kept: the card-note vs panel-note pair (two doors onto one function — the point is both doors),
every reconcile/lock test (checklist 4, 5, 25, 32, 37), every shadow / `would_*` test (1, 2),
every demoted-staffer and non-staff refusal.

### `tests/cogs/moderation/test_automod.py` (76) and `test_quiet_pins.py` (15) — unchanged

Considered and kept: the two bounded-number modal tests check different bounds on different
rules (and the caps label); the three arming-confirm tests are three different moves; the apply
button's literal `custom_id` is a persisted key a restart must still dispatch.

### `tests/live/` — 74 collected, unchanged (read only)

Kept whole: the deliberate exception to tests-mirror-the-package (`tests/live/__init__.py`),
the refusal-in-words tests (global rule), and the one Discord-exercising self-test run. The two
operator-write refusals (`test_refusals.py`, `test_selftest.py`) hit different routes through
the same gate; kept as access tests.

## Not done

- `test_modmail.py` (4047 lines) and `test_db.py` (3276) were read by test name, targeted
  regions and a structural near-duplicate scan (normalised AST, difflib ratio ≥ 0.7), not line
  by line. Further merges may exist there that the scan did not rank.
