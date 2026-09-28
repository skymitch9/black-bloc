# Test audit 2026-09-28 — `tests/api/tools/` and `site/mock/*.test.mjs`

> **Audience:** whoever merges the six `test-audit-*` branches, and any later session asking
> "why did this test change". **Status:** TRACKED. **Last verified: 2026-09-28** — every figure
> below was measured on branch `test-audit-apitools` (base `origin/main` `6dac0fe`): the slice
> run under `coverage`, the full suite, `ruff check .`, and all eight node files the deploy
> gate runs. ⚠️ **NOT checked:** the other five slices (sibling branches), browsers, Fly, Discord.

Owner's ask: *"Check all unit tests and make sure each is specific and needed. No redundant,
brittle, or unneeded ones"*. Only test files changed; no source file was touched.

## Result

| | Before | After |
|---|---|---|
| Python test functions in `tests/api/tools/` | 805 | 798 |
| Python items collected in the slice | 1148 | 1143 |
| Node assertion calls in the eight `.test.mjs` | 449 | 429 |
| Slice executed lines under `coverage` (`--source=black_bloc`) | 30189 in 190 files | 30189, **no line lost** |
| Full suite `pytest -q -n 16` | — | 9421 passed |

Category totals, counted per change row in the tables below (one row may fix several literals): **redundant 12**, **brittle 39**,
**unneeded 5**, **not specific 8** (4 renames, 4 sentence checks added to refusals that only
checked a status).

## Coverage

Measured with `coverage run --source=black_bloc -m pytest -q -p no:randomly tests/api/tools`
before any change and again at the end, compared file by file (executed-line sets): for every
one of the 190 source files the after-set is a superset of the before-set, and the totals are
equal (30189). The comparison script lived outside git
(`C:/lcw/bb-test-audit-apitools-cov/diff.py`). Node files have no coverage tool; every node
assertion removed is listed below with the assertion that still covers it.

## Python — per file

Files with **no change** (read in full; nothing redundant, brittle or unneeded found worth the
churn): `test_chat_memory.py` (9), `test_honeypot.py` (10), `test_minutes.py` (15),
`test_mod.py` (29), `test_pings.py` (39), `test_preview.py` (8), `test_roles.py` (15),
`test_tempvoice.py` (22).

| File | Tests before → after | Change | Category | Why |
|---|---|---|---|---|
| `test_applications.py` | 36 → 35 | `test_a_form_needs_a_name_a_heading_and_a_role` + `test_a_form_created_with_neither_a_name_nor_a_heading_is_refused_in_words` → one parametrised `test_a_form_without_both_a_name_and_a_heading_is_refused_in_words` | redundant | same route, same refusal, input differs |
| | | `…capped_at_five` → `…capped`; `range(6)` / `"at most 5 boxes"` read `forms.QUESTIONS_MAX` | brittle | restated a constant |
| | | remove route: dropped `"…removed" in kinds` beside `kinds.count(…) == 1` | redundant | implied by the count |
| `test_birthdays.py` | 16 → 16 | `test_a_member_id_that_is_not_a_number_is_a_sentence` now asserts the message | not specific | name promised a sentence, test only read the status |
| `test_chat.py` | 76 → 76 | chat settings key set: 29 hand-typed keys → `{k for k in KEY_TYPES if k.startswith("chat_")}` | brittle | every new chat key broke it |
| | | trope counts `11` / `10` / `"11 voices"` → `len(personas.TROPES)` | brittle | restated the pool size |
| | | `budget.sections == 3` → `knowledge.HITS_DEFAULT`; `cap == 4096` → `directory.DIRECTORY_BYTES`; `note_chars == 240` / `241` → `channel_notes.NOTE_CHARS` | brittle | restated constants |
| | | review `reason_word`, suggestion word, markdown heading → `REVIEW_WORDS[...]` defaults | brittle | member-facing words are settings keys |
| `test_events.py` | 45 → 45 | forum name/tags → `FORUM_CHANNEL_NAME`, `STATUSES`; moved-room line → `EVENTS_MOVED_LINE` | brittle | literal copies of constants / a settings default |
| | | `test_moving_an_event_black_bloc_never_heard_of_is_a_404` asserts the sentence | not specific | refusal read as a bare status |
| `test_frontdoor.py` | 10 → 10 | `test_the_three_labels_are_the_words_the_card_draws` → `test_the_posted_door_never_times_out_and_every_button_is_a_door_button`; dropped `LABEL_DEFAULTS[TICKET] == "Ask staff privately"` | brittle + not specific | pinned a settings default; the name described what it no longer asserted (labels are asserted in the first post test) |
| `test_golive.py` | 72 → 72 | `test_the_session_limit_is_clamped` seeds two sessions and asserts `limit=0` → 1 row, `limit=10000` → 2 | not specific | it asserted only `200`, which proves nothing about clamping |
| | | ping states, window source word, marathon window refusal, staff-off clause, replay line, treated-as-live line → registry defaults / module constants | brittle | long member-facing literals |
| `test_guides.py` | 50 → 50 | guide counts `12` / `27` → derived from `pure.seed_entries()` | brittle | restated the seed length |
| | | saved line → `SAVED_SAID.format(title=…)`; `seed_do` → the seed step itself | brittle | literal copies |
| | | read-bucket test: `bucket._seen[...] = …` → `bucket.take(key, now=later)` | brittle | wrote a private dict; the public `now=` does the same without timing risk |
| | | `…cannot_confirm_a_staff_guide_or_one_that_is_not_published` → `…confirming_a_staff_guide_is_told_there_is_no_such_guide`, + sentence check | not specific | the unpublished half was never tested |
| `test_marathon_feeds.py` | 12 → 12 | `hours == 6`, `action_default == "add"` → `web.store.default(...)`; sources list → `list(mf.PICKS)` | brittle | restated defaults / the picks table |
| `test_marathons.py` | 40 → 40 | event modes → `MARATHON_EVENT_MODES`; read-gap refusal → `marathon.BAD_POLL`; match word → `MATCHED_WORDS[BY_LINK]` | brittle | literal copies |
| `test_members.py` | 18 → 18 | `50` / `100` → `members.PER_PAGE` / `PER_PAGE_MAX` | brittle | restated route constants |
| `test_modmail.py` | 24 → 24 | panel title → `MODMAIL_PANEL_TITLE_DEFAULT`; forum shape → `FORUM_CHANNEL_NAME`, `FORUM_TAG_NAMES` | brittle | literal copies |
| | | snippet and block refusals assert a sentence | not specific | status-only |
| `test_polls.py` | 55 → 54 | removed `test_with_the_mode_on_a_real_channel_is_still_refused_in_words` | redundant | body and fixtures identical to `test_the_form_will_not_post_outside_the_test_channel` |
| | | shadow note → `pure.SHADOW_NOTE` | brittle | literal copy |
| `test_posts.py` | 34 → 33 | removed `test_the_put_back_route_is_gone` | unneeded | asserts FastAPI's 404/405 for a route that does not exist |
| | | caps, title cap, styles, saved line → `posts.CAPS`, `TITLE_MAX`, `STYLES`, `SAVED_SAID` | brittle | restated constants |
| `test_raidtrain.py` | 36 → 36 | status word, poll minutes, slot bounds → `STATUS_WORDS`, `web.store.default`, `SLOT_*` | brittle | restated constants |
| | | dropped `assert await web.db.conn.execute("SELECT * FROM raid_trains")` | unneeded | a cursor is always truthy; the next line is the real check |
| `test_requests.py` | 64 → 62 | `test_a_status_nothing_can_be_in_is_refused_in_words` + `test_a_status_filter_the_bot_does_not_know_is_refused_by_name` → one parametrised `test_a_status_filter_nothing_can_be_in_is_refused_by_name` | redundant | same route and refusal, input differs |
| | | removed `test_a_due_date_stays_a_plain_date_on_the_way_out` | redundant | `row["due_on"] == "2026-09-15"` in `test_a_filed_row_carries_every_field_the_requests_page_reads` implies it |
| | | forum name/tags → `FORUM_CHANNEL_NAME`, `FORUM_TAG_NAMES` | brittle | literal copies |
| | | dropped a no-op `await wf.web_rows_in(web.db)` in the ready-route test | unneeded | result discarded |
| `test_rolemenus.py` | 52 → 51 | removed `test_a_role_that_is_gone_leaves_the_menu_alone`; its `no_such_role` error-code check moved into `test_a_bad_role_late_in_the_list_leaves_the_heading_alone` | redundant | the checklist-12 test asserts everything else it did, with a stronger input |
| | | `"at most 25 roles"` → `OPTIONS_MAX`; the name/heading refusal asserts a sentence | brittle / not specific | |
| `test_youtube.py` | 18 → 17 | removed `test_the_videos_route_is_gone_rather_than_answering_an_empty_list` | unneeded | FastAPI's 404 for a route removed at v139; the "nine upload fields are ABSENT" check code-notes names is kept |
| | | `live_minutes == 5`, `live_end_misses == 2` → `web.store.default(...)` | brittle | restated defaults |

### Kept on purpose (looked redundant, a guard kept them)

| Test(s) | Guard |
|---|---|
| every `test_every_*_route_needs_a_session` / `…refuses_a_non_staff_visitor` and each file's staff-only loops | access tests |
| `test_golive.py::test_the_website_never_says_a_link_it_did_not_check_was_checked` beside `test_linking_a_member_stores_the_login_and_says_it_was_not_checked` | checklist 10 |
| `test_minutes.py::test_the_website_never_writes_the_bare_kind_beside_the_web_one`, `test_applications.py::test_each_form_write_…exactly_one_log_row`, `test_requests.py::test_resuming_from_the_site_leaves_one_row_and_not_two`, `test_tempvoice.py::test_the_web_rename_line_says_it_came_from_the_website` | checklist 34 / `web.` log-row tests |
| `test_posts.py` block tests, including the literal kind order in `test_the_blocks_section_lists_every_kind…` | blocks API guard (order) |
| `test_guides.py::test_stale_all_is_never_read_as_a_guide_called_stale` | route-order regression named in its docstring |
| `test_golive.py::test_the_history_sweep_links_the_newest_channel…` whole-dict assert | `autolink-design.md` names the exact-dict assertion |
| `test_mod.py` untouched | `automod-panel-design.md` used it as the proof a refactor moved nothing; nothing in it was worth the churn |
| `test_youtube.py::test_status_says_whether_the_key_is_set…` `UPLOAD_FIELDS` absence | code-notes `api/tools/youtube.youtube_status` |

## Node — `site/mock/*.test.mjs`

All eight are run by `scripts/deploy.ps1` by path; none was renamed or deleted.

| File | Removed / changed | Category | Still asserted by |
|---|---|---|---|
| `clipmd.test.mjs` | `hasNot('**Welcome')`, `hasNot('__')` on the Docs fragment | redundant | the exact `is(where, found, DOCS_WANTED)` above them (its own comment said so) |
| | `hasNot('alert')`, `hasNot('color:red')`, `hasNot('font-weight')` | redundant | exact `is(…, 'Before and after')` |
| | `hasNot('\n\n\n')` in whitespace; the now-unused `hasNot` helper | redundant | exact `is(…, 'lots of space\n\nthen this')` |
| `golive-join.test.mjs` | ten hand-listed per-drawer `same(...)` lines → one loop over every `DRAWERS` entry with `keys` | redundant (table-driven) | the loop covers the same ten drawers and any added later |
| | `home('pings').length === 10` → the pings drawer equals every contract key its `holds` takes that no other home names | brittle | the three explicit "not in Ping roles" checks stay |
| | `gdqRow` (second lookup of `gdq`); `spotlightCards(SPOTLIGHT)[0].pinned` second time | redundant | `cards[0].pinned` above |
| `layout.test.mjs` | `Open is in the left column whatever the heights` single line → its run `[90, 900, 5, 5]` joined the `RUNS` invariant loop; runs already pinned exactly (`[10,10]`, `[100,5]`, `[5,5,5,5]`, the Requests run) left the loop | redundant | the loop's "first block is on the left" + the exact `columnSplit` lines |
| `marathon-words.test.mjs` | `the word a person reads is BaF` (`BAF === 'BaF'`) | unneeded | `headerCounts` / `dayTitle` / `archiveCounts` all assert the `BaF` word in output |
| | `the drawer is five parts…` → `the drawer draws its parts in order, header first and the moves last` | not specific | it lists seven parts |

`discordmd.test.mjs`, `discordmock.test.mjs`, `labels.test.mjs`, `mdformat.test.mjs`: no change.

## Real bugs found

None. No test revealed a source defect.

## Not done

- The `Namu pings` / `{name} pings` role-name literals in `test_pings.py` and `test_golive.py`
  were left: short, and they are the observable name the route makes.
- `test_mod.py`'s `threshold == 5` and page size `10` literals were left (see the kept table).
