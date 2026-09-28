# Test audit 2026-09-28 — slice top1 (`tests/test_actionlog.py` … `tests/test_marathon_ladyarcaders.py`)

> **Audience:** the conductor merging the six audit slices, and any later session asking "why did
> this test change?". **Status:** TRACKED. **Last verified: 2026-09-28** on branch
> `test-audit-top1` (base `6dac0fe7`): slice run 1763 passed, full suite `pytest -n 16` 9507 passed,
> `ruff check .` clean, coverage guard 0 lines lost.
> ⚠️ **NOT checked:** duplicates against the other five slices were not searched for systematically
> (only noted where one was seen); `tests/test_logkinds.py` lines 1–1070 were grepped for counts
> and literals, not read line by line (the file is a guarded registry suite).

Owner's ask (2026-09-28): *"Check all unit tests and make sure each is specific and needed. No
redundant, brittle, or unneeded ones."* Scope: the 51 `tests/test_*.py` files directly in
`tests/` from `test_actionlog.py` to `test_marathon_ladyarcaders.py`. Tests only — nothing under
`black_bloc/`, `site/`, `scripts/`, `tests/conftest.py`, `tests/loopback.py` or `tests/fixtures/`
was touched.

## Totals

| Measure | Before | After |
|---|---|---|
| Collected test cases (slice) | 1682 | 1763 (parametrize ids expand) |
| Test functions (slice) | 1457 | 1422 |
| Executed `black_bloc` lines (slice run) | 24712 / 59125 | 24712 / 59125 |
| Lines executed before and not after | — | **0** (per file, set comparison) |
| Full suite `pytest -n 16` | — | 9507 passed, 0 failed |

Coverage method: `coverage run --source=black_bloc -m pytest -q -p no:randomly <slice files>`
before any change and after the last one, `coverage json`, then for every source file the after
set of executed lines checked as a superset of the before set. Also run once midway (0 lost).

Category totals, counted per change listed below (one row can carry two): **redundant 20**,
**brittle 23**, **unneeded 4**, **not specific 8**. No real bug was found.

## Per file

Files not listed in this table were read and left unchanged (every test specific and needed):
`app`, `button_block`, `channel_drafts`, `channel_notes`, `channel_reach`, `chat_voice`,
`dbsnapshot`, `handoff`, `honeypot`, `knowledge`, `marathon_archive`, `marathon_channels`,
`marathon_events`, `marathon_fastestfurs`, `marathon_horaro_events`, `marathon_inbox`, plus the
guarded files listed under *Kept*.

| File | Cases before → after | What changed | Category |
|---|---|---|---|
| `test_actionlog.py` | 33 → 33 | `test_every_send_logs_call_site_passes_only_the_feature_name`: exact `len(found) == 21` → non-empty (every new Logs button broke it; the real guard is the shape set). `test_send_logs_reads_the_two_knobs_itself…`: dropped the parameter-order list, kept the defaults it is named for. | brittle |
| `test_applications.py` | 57 → 57 | `NO_ANSWER` / `DENIED_SAID` / `REMOVED_SAID` constants instead of their sentences; duplicate `TRANSITIONS[WITHDRAWN] == ()` dropped from the withdrawn-buttons test (first transitions test pins it); `test_the_own_list_key_is_on_by_default…` renamed `…_is_read_off_its_own_key_as_a_bool` (it never checked a default). | brittle, redundant, not specific |
| `test_automod.py` | 44 → 54 | `test_invites_attachments_caps_and_bad_words` (five rules in one body) and `test_rule_validation_refuses_what_discord_would_refuse` (seven refusals in one body) parametrized with ids; the non-refusal half split to `test_an_unknown_rule_is_refused_and_lists_are_read_tidied`. | not specific |
| `test_birthdays.py` | 57 → 56 | `test_the_colour_falls_back…` parsed the shipped colour, so a parse and a fallback were indistinguishable — now parses `#12ab34` and compares the fallback to `BIRTHDAY_COLOR`. Template, post-count and block-word sentences → `BIRTHDAY_TEMPLATE` / `BIRTHDAY_POST_WORDS` / `BUTTON_BLOCK_DEFAULTS`. Removed `test_the_modal_never_guesses_a_year` (the parametrized parse table pins both year cases). | not specific, brittle, redundant |
| `test_block_look.py` | 7 → 7 | `"Live now"`, `10`, `5` → `BLOCKS_LIVE_DEFAULTS`. | brittle |
| `test_bot.py` | 16 → 16 | `TOP_LEVEL_NOW = 33` → `len(STAFF_COMMANDS \| MEMBER_COMMANDS)` and the stale "30 slots" docstring corrected; `RETIRED_GROUPS` assert dropped (implied by `groups == []`); mode-off test asserts `bot.status is Status.online` instead of private `_connection._status`. | brittle, redundant |
| `test_chat.py` | 131 → 133 | `test_asking_who_holds_a_role_still_reaches_who_has_when_nobody_is_named` folded into the data/route phrase table (same `classify` path, three more rows). | redundant |
| `test_chat_check.py` | 14 → 14 | Six "left exactly as written" copies (real channel, first-word role, everyone/here, named member, real mentions, `#1`/URL fragment) → one parametrized `test_a_reply_that_names_only_real_things_is_left_exactly_as_written`; every case now also checks the text, not only `fixed == 0`. | redundant |
| `test_chat_data.py` | 55 → 70 | `wanted_role` (11 asserts) and `is_online` (6 asserts) parametrized; reply sentences → `NOTHING_HELD`, `MENUS_LIVE_IN`, `NOBODY_HOLDS_IT`, `NO_SUCH_ROLE`, `ONLINE_NOW`, `NOBODY_ONLINE`. | not specific, brittle |
| `test_chat_distil.py` | 16 → 16 | Five "the sweep sends nothing" copies (memory off, opted out, staff conversation, one-liner, capped month) → one parametrized test; every case now also asserts no profile was written. | redundant |
| `test_chat_llm.py` | 97 → 101 | Four ladder tests → one table with ids; the `?` / no-`?` grounding tests (identical bodies) → one parametrized test keeping both regression notes; window size `20` → `WINDOW_TURNS * 2`; a grounding-note sentence already implied by `GROUNDING_NOTE in said` dropped. | redundant, brittle |
| `test_chat_memory.py` | 36 → 53 | Three `parse_distilled` no-op tests → one parametrized (8 ids); `test_the_rules_each_name_themselves` (13 asserts) parametrized. | redundant, not specific |
| `test_chat_panel.py` | 65 → 65 | Broken-template fallback compared to `CHANNEL_NOTE_WORDS` instead of a `startswith` literal; key literal → `CHANNEL_NOTE_SAVED_KEY`; one assert implied by the line above dropped. | brittle, redundant |
| `test_chat_review.py` | 43 → 43 | Digest line and placeholder line → `REVIEW_WORDS` defaults. | brittle |
| `test_command_errors.py` | 24 → 24 | Retry minutes `10` → `ERROR_RETRY_MINUTES`. | brittle |
| `test_command_visibility.py` | 26 → 26 | `len(HIDDEN_WHEN_OFF) == 17` dropped — the dict equality on the line above pins all 17. | redundant |
| `test_directory.py` | 33 → 33 | Channel ids were `abs(hash(name)) % 10_000`: `str` hashing is randomised per process, so two channels could collide on some runs. Now `zlib.crc32`. | brittle |
| `test_emoji.py` | 12 → 19 | Heart test and TONEABLE-set test merged into one parametrized glyph test (each glyph: not toneable AND unchanged at every tone). | redundant |
| `test_events.py` | 172 → 172 | Propose-block, upcoming-block, moved-line and scheduled-name-fallback literals → `BUTTON_BLOCK_DEFAULTS` / `BLOCKS_LIVE_DEFAULTS` / `EVENTS_MOVED_LINE` / `EVENTS_SCHEDULED_NAME_TEMPLATE`. | brittle |
| `test_golive.py` | 133 → 137 | Six `live_author` and seven `ended_author` copies → two parametrized tables (the unreadable-wording caplog tests stay separate); live-block words → `BLOCKS_LIVE_DEFAULTS`; `test_the_gone_quiet_footer…` restated three constants as literals → asserts only the `/golive` it is named for. | redundant, brittle, unneeded |
| `test_groq.py` | 19 → 22 | Status loop → parametrize; the two "close a client that never opened" tests → one parametrized, dropping the private `_session is None` assert. | redundant, brittle |
| `test_guides.py` | 44 → 44 | Seed count `27` restated four times under names saying "eighteen" → `len(seed_entries())`, two tests renamed; voice-room title and step count → the shipped seed entry; `== 11` dropped from `links_for` (the derived member-command count is already compared); `isinstance(…, dict)` asserts dropped. | brittle, not specific, unneeded |
| `test_link_buttons.py` | 5 → 5 | Card heading/line literals → `BLOCKS_LIVE_DEFAULTS`. | brittle |
| `test_linkcheck.py` | 9 → 21 | Six status/exception loop tests → two parametrized tests with ids; removed `test_the_body_is_never_read_because_only_the_status_is_asked_for` — its fake never hands our code a body, so it asserted only the fake. | redundant, unneeded |
| `test_llm.py` | 13 → 15 | SDK-failure loop → parametrize, and `test_a_refusal_carries_the_status_it_answered_with` folded in (same `Status` fake, same path; status now checked for every case). | redundant |
| `test_logkinds.py` | 55 → 63 | Four "routine from either door, files under chat" copies (notes, drafts, reach, tones) → one parametrized over the 11 kinds plus `test_seeding_the_channel_drafts_is_routine`; `len(FEATURES) == 22` twice → uniqueness against its own length. | redundant, brittle |
| `test_logs_panel.py` | 20 → 18 | Removed `test_the_toggle_wears_the_move_it_would_make` (both labels pinned by the show-more and `send_logs` tests) and `test_the_panel_takes_a_minutes_number_like_every_other_panel` (`isinstance(View)` is discord.py's behaviour; timeout and footer pinned elsewhere). | redundant, unneeded |
| `test_loops.py` | 12 → 12 | `BEFORE_LOOPS = 22` exact count → non-empty; the KI-24 guard itself (`missing` must be empty) is unchanged. | brittle |
| `test_marathon_feeds.py` | 22 → 22 | `SEEDS[3]` / `SEEDS[4]` index lookups → lookup by login / membership (seed order is pinned once, in `test_the_seeds_are…`); per-pick `UNKNOWN_PICK` / hint asserts dropped (the every-pick loop covers them). | brittle, redundant |
| `test_marathon_ladyarcaders.py` | 27 → 27 | Magic `3000` / `2000` → `SEEN_LIMIT`. | brittle |

## Kept, and the guard that kept it

| File / test | Why it stayed as it was |
|---|---|
| `test_config.py` (all) | Owner rule: config only from `config.py`. |
| `test_guard.py` (all) | Owner rule: the `TEST_MODE` guard. |
| `test_frontdoor.py` (all) | Front-door owner guarantees; every-word-is-a-key. |
| `test_command_errors.py` (all behaviour) | Refusals said in words; checklist 8, 29, 30, 36. |
| `test_command_visibility.py` (all behaviour) | Command-visibility owner rules; the `HIDDEN_WHEN_OFF` dict equality is the owner's "B" decision. |
| `test_bot.py` `STAFF_COMMANDS` / `MEMBER_COMMANDS` pins | Command visibility (owner). |
| `test_golive_replay.py` (all, incl. the owner's six words) | Golive replay rules (fuzzy counts as live). |
| `test_golive.py` `test_render_matches_the_incumbent_wording` | Pins the incumbent bot's wording on purpose. |
| `test_marathon.py` (all, incl. `test_the_shipped_words_are_the_registrys_defaults`) | Marathon rules the owner set. |
| `test_logkinds.py` (everything but the two changes above) | Logkinds registry guard; checklist 34 traces untouched. |
| `test_loops.py` reconcile tests (`sleep(0)` is a yield, not timing) | Checklist 37 lock tests. |
| `test_knowledge.py` grounding "quote it rather than inventing" negative | `code-notes.md` names it as the regression. |
| `test_automod.py` `test_the_defaults_are_the_incumbents_live_config` | Pins the incumbent's live config on purpose. |
| `test_handoff.py` key and table pins | Key tests; `TABLES` is a write allow-list. |
| `test_guides.py` seed-sync tests | Owner rule 2026-09-25: staff guide edits survive a seed sync. |
| `test_applications.py` / `test_events.py` transition tests | Owner rule: staff final say. |
| `test_chat_panel.py` `store._cache[...]` write | The only way past the store's validator to plant a broken template; the fallback is the point. |
| `test_channel_drafts.py` `len(seed) == 94` | A fixed data catalog; no derived value exists and the count guards truncation. |

## Cross-slice duplicates for the conductor

None were confirmed. `test_applications.py::test_the_site_link_needs_an_origin_and_points_at_the_role_menus_page`
and `test_events.py::test_the_site_link_needs_an_origin_and_points_at_the_events_page` have the same
shape but test two modules' own `site_page_url`, so both stay. No search was made of the other
five slices.

## Findings (not fixed — tests only)

No real bug. Three observations for whoever owns the every-word-is-a-key rule:

- `black_bloc/chat_data.py` posts module constants (`NOTHING_HELD`, `NO_SUCH_ROLE`,
  `NOBODY_HOLDS_IT`, `ONLINE_NOW`, `NOBODY_ONLINE`, `MENUS_LIVE_IN`) into member-facing chat
  replies; they are not settings keys.
- `black_bloc/applications.py` card sentences (`DENIED_SAID`, `REMOVED_SAID`, `WITHDRAWN_SAID`,
  `NO_ANSWER`) are constants, not keys.
- `black_bloc/golive.py` `PANEL_TIMEOUT_FOOTER` is a constant.

Whether these count as "words the bot posts" under the 2026-09-17 rule is the owner's call; the
tests now read the constants, so a later move to keys needs only the import changed.

## Not done

- `tests/test_logkinds.py` lines 1–1070 were not read line by line (grepped for exact counts,
  literals and copy-paste shapes only).
- No systematic cross-slice duplicate search.
