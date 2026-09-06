# Test-suite profile — where the 5188 tests actually spend their time

> **Audience:** the owner (the "do we truly need 5186 tests?" question) and
> Claude sessions sizing a test change. **Status:** TRACKED.
> **Last verified: 2026-09-05** — every number below was measured on this
> date, on branch `worktree-agent-a8faa99c1ac0f0922` off `5c9c2a6` (v93), against a
> clean worktree, with `pytest 9.1.1` / Python 3.12.10 / 32 logical CPUs, and
> each table names the exact command that produced it.
> ⚠️ **This is a REPORT. No test, no source file and no fixture was changed.**
> ⚠️ **NOT measured, and not estimated into any table below:**
> **(a)** the full serial (`-n 0`) run — started, killed at 15% when it
> projected to ~25 min against a 15-min budget, and the readings it had taken
> were contaminated by concurrent tool calls, so no full-serial total appears
> anywhere here; serial figures below cover the ten heaviest files (964 tests)
> and `test_contract.py`, run alone with nothing else in flight.
> **(b)** coverage — no `--cov` run was made, so "what a deletion would lose"
> is argued from reading the tests, never from a coverage delta.
> **(c)** the `tests/live/` suite (59 tests, deselected by config — see §5).
> **(d)** memory/IO counters; only wall time and pytest's own durations.

**The one-line answer:** the suite's **size is not the problem — its fixture
shape is.** 3% of the tests cost 19% of the wall clock, and the cost is one
function-scoped fixture, not the assertions.

---

## 1. Where the time goes

### 1.1 The totals

| Measure | Value |
|---|---|
| Tests collected / run | **5188** (5247 collected, 59 deselected by `-m 'not live'`) |
| Test files | **99** |
| Wall clock, `-n auto` (32 workers) | **79.12 s** |
| Collection alone | **1.90 s** |
| Failures / errors | 0 |
| Accounted CPU across all workers | **1726.75 s** |
| Distinct test functions (before parametrisation) | 3943 |

```
pytest -q -p no:cacheprovider --durations=0 -rsx -n auto   # 5188 passed in 79.12s
pytest -p no:cacheprovider --collect-only -q               # 5188/5247 in 1.90s
```

⚠️ **Accounted CPU (1726.75 s) is 22× the wall clock** because 32 xdist workers
run at once, and it includes each worker's contention on the one disk. It is
useful for *ranking* work, and useless as a per-test cost. Every per-test cost
claim below is taken from a **serial** run instead.

### 1.2 The top 40 slowest tests, and what makes each slow

**37 of the top 40 are ids of one single parametrised test.** The list is
therefore given as its three distinct causes rather than forty near-identical
lines.

| Rank | Test | s (`-n auto`) | What makes it slow |
|---|---|---|---|
| 1 | `tests/test_pings.py::test_twenty_six_streamers_fill_two_menus_and_shrink_back_to_one` | 6.36 | **Work in the test body.** Builds 26 streamer rows and re-paginates two role menus. Serial: 0.84 s call, 0.06 s setup. No DB churn, no sleep — it is genuinely doing 26 things. |
| 2 | `tests/cogs/content/test_pings.py::test_a_capped_select_names_the_streamer_pings_panels_not_the_site` | 5.28 | Same shape — fills past the 25-option Discord cap. Serial: 0.68 s call. |
| 3 | `tests/test_panels.py::test_no_cog_writes_its_own_copy_of_a_library_helper` | 4.22 | **An AST scan of every cog in `black_bloc/`** (the checklist guard against a cog re-implementing `panels.py`). Serial: 2.64 s call, ~0 setup. Cost scales with the source tree, not the suite. |
| 4–40 | `tests/api/test_contract.py::test_every_route_answers_with_the_keys_the_pages_read[…]` (37 ids, 1.81–3.71 s each) | 1.81–3.71 | **A 321-line function-scoped fixture, re-run per route.** See §2.2. Not a real SQLite *file* problem, not a sleep, not a subprocess, not network — it is 57 `await`ed seed writes plus a fresh schema build plus a fresh FastAPI app, 149 times over. |

```
# ranking (parallel):
pytest -q -p no:cacheprovider --durations=0 -n auto
# the three individual tests, serially, alone:
pytest -q -p no:cacheprovider --durations=0 \
  tests/test_pings.py::test_twenty_six_streamers_fill_two_menus_and_shrink_back_to_one \
  tests/cogs/content/test_pings.py::test_a_capped_select_names_the_streamer_pings_panels_not_the_site \
  tests/test_panels.py::test_no_cog_writes_its_own_copy_of_a_library_helper   # 3 passed in 4.46s
```

**Causes explicitly checked for and NOT found:** no test performs network I/O;
no `time.sleep` longer than 0.05 s exists anywhere (`tests/api/test_selftest_api.py`
0.01 s, `tests/cogs/test_presence.py` 0.05 s, the rest are `asyncio.sleep(0)`
yields); exactly one file shells out — `tests/scripts/test_sync_personality_pool.py`
runs `git` via `subprocess`, and the whole file costs **0.67 s** for 7 tests.

### 1.3 How concentrated is the cost?

Denominator is all **5188** tests; the ~1800 that never register a duration
above pytest's 0.005 s floor are counted as zero.

| Slice | Tests | Accounted s | Share |
|---|---|---|---|
| Slowest **1 %** | 52 | 115.09 | 6.7 % |
| Slowest **5 %** | 259 | 377.88 | 21.9 % |
| Slowest **10 %** | 519 | 586.00 | 33.9 % |
| Slowest 25 % | 1297 | 1047.12 | 60.6 % |
| **Bottom 90 %** | **4669** | **1140.75** | **66.1 %** |

The same slice, measured **serially** on the ten heaviest files (964 tests,
128.28 s wall, nothing else running):

| Slice | Tests | Serial s | Share |
|---|---|---|---|
| Slowest 1 % | 10 | 6.28 | 5.0 % |
| Slowest 5 % | 48 | 21.26 | 17.1 % |
| Slowest 10 % | 96 | 37.01 | 29.7 % |
| **Bottom 90 %** | **868** | **87.50** | **70.3 %** |

⚠️ **Read this table the right way round.** There is no fat tail of a few
pathological tests to delete. Two-thirds of the time is the *broad middle* —
4669 tests each costing 50–250 ms, and **almost all of that is fixture setup**
(§2). You cannot fix a distribution like this by deleting tests; you fix it by
making the thing every test pays for cheaper.

### 1.4 The ten heaviest files

| # | File | Tests | Accounted s (`-n auto`) | **Serial s** | Serial ms/test |
|---|---|---:|---:|---:|---:|
| 1 | `tests/api/test_contract.py` | 153 | **221.41** | **64.01** | 418 |
| 2 | `tests/cogs/content/test_pings.py` | 176 | 81.99 | 12.61 | 72 |
| 3 | `tests/cogs/moderation/test_modmail.py` | 130 | 64.68 | 9.05 | 70 |
| 4 | `tests/cogs/content/test_golive.py` | 129 | 49.90 | 8.00 | 62 |
| 5 | `tests/api/tools/test_chat.py` | 45 | 48.97 | 15.10 | 336 |
| 6 | `tests/api/tools/test_mod.py` | 72 | 46.13 | 20.30 | 282 |
| 7 | `tests/cogs/community/test_events.py` | 136 | 43.94 | 9.06 | 67 |
| 8 | `tests/cogs/content/test_youtube.py` | 93 | 43.58 | 5.64 | 62 |
| 9 | `tests/api/tools/test_rolemenus.py` | 69 | 42.07 | 14.44 | 209 |
| 10 | `tests/api/tools/test_applications.py` | 58 | 40.63 | 15.61 | 269 |

```
pytest -q -p no:cacheprovider --durations=0 tests/cogs/content/test_pings.py \
  tests/cogs/moderation/test_modmail.py tests/cogs/content/test_golive.py \
  tests/api/tools/test_chat.py tests/api/tools/test_mod.py \
  tests/cogs/community/test_events.py tests/cogs/content/test_youtube.py \
  tests/api/tools/test_rolemenus.py tests/api/tools/test_applications.py \
  tests/api/tools/test_requests.py            # 964 passed in 128.28s
pytest -q -p no:cacheprovider tests/api/test_contract.py    # 153 passed in 64.01s
```

⚠️ `test_contract.py` is **3 % of the tests and 13 % of the accounted CPU.** It
does not appear in the parallel run's per-file list unless the parser allows
spaces in test ids — its ids look like `[GET /api/rolemenus/requests]`. A naive
`\S+` regex silently drops the single heaviest file in the suite.

---

## 2. Setup cost versus test cost

### 2.1 The split

`--durations` reports `setup`, `call` and `teardown` separately. The
proportion is stable across regimes, which is what makes it a real finding
rather than an xdist artefact:

| Run | Tests | setup | call | teardown |
|---|---:|---:|---:|---:|
| Whole suite, `-n auto` | 5188 | **1455.89 s — 84.3 %** | 217.75 s — 12.6 % | 53.11 s — 3.1 % |
| Ten heaviest files, **serial** | 964 | **99.67 s — 80.1 %** | 24.13 s — 19.4 % | 0.65 s — 0.5 % |
| `test_contract.py`, **serial** | 153 | **65.02 s — 98.6 %** | 0.78 s — 1.2 % | 0.15 s — 0.2 % |

```
pytest -q -p no:cacheprovider --durations=0 -n auto
pytest -q -p no:cacheprovider --durations=0 <the ten files above>
pytest -q -p no:cacheprovider --durations=0 tests/api/test_contract.py
```

🔴 **The 149 contract assertions cost 0.78 seconds. Getting ready to make them
cost 65.02.** Every route check in that file could be deleted and the suite
would get 1.2 % faster.

### 2.2 The five most expensive fixtures — measured, not guessed

Each building block was timed 20× in isolation against this worktree.

| # | Fixture | Where | Scope | Measured cost, each | Tests paying it | CPU floor |
|---|---|---|---|---:|---:|---:|
| 1 | `seeded` | `tests/api/test_contract.py:211` | **function** | **~428 ms** total setup, of which **~293 ms** is its own body | 149 | **63.8 s** |
| 2 | `client` → `create_app()` + `TestClient` | `tests/api/conftest.py` | **function** | **83.6 ms** median | 1035 | **86.5 s** |
| 3 | `web_db` / per-cog `db` → `Database.connect()` | `tests/api/conftest.py` + 45 cog files | **function** | **51.0 ms** median | **3298** | **168.2 s** |
| 4 | `SettingsStore(...).load()` | `tests/api/conftest.py` | function | 0.2 ms | 1035 | 0.2 s |
| 5 | `load_settings()` | both conftests + every cog file | function | 0.6 ms | ~4300 | 2.6 s |

```
# black_bloc.storage.db.SCHEMA_VERSION == 32
Database.connect()        x20: median  51.0ms  mean 51.8  min 49.5  max 58.7
create_app()+TestClient   x20: median  83.6ms  mean 97.4
SettingsStore.load()      x20: median   0.2ms
load_settings()           x20: median   0.6ms
# and: 3298 of 5188 collected tests live in one of the 46 files that build a
# real Database in a fixture; 1035 of those are under tests/api/ and also
# build an app.
```

**What this says, in order:**

1. ⚠️ **`Database.connect()` is the tax on the whole suite.** It builds
   **schema v32 into a fresh on-disk SQLite file**, and it is
   **function-scoped in all 46 files that use it**. 3298 tests × 51 ms =
   **168 s of CPU spent creating and destroying 3298 identical databases.**
   Nothing about that number depends on how many assertions the suite makes.
2. **`create_app()` + `TestClient` costs 84 ms** and is likewise rebuilt per
   test, for all 1035 api tests. The app has no per-test state that a fresh
   database does not already reset.
3. **`seeded` is the extreme case of the same mistake.** 321 lines, 82
   statements, **57 `await`ed writes** across every feature in the product —
   cases, events, tickets, polls, grants, links — rebuilt from nothing for
   **each of 149 routes.** Its own docstring says why:
   *"every contract entry runs against a fresh seed."*
4. **Fixtures 4 and 5 are exonerated.** `SettingsStore.load()` and
   `load_settings()` are together under 1 ms and are not worth touching.

**This is the whole finding:** a suite whose time is 80–98 % fixtures is fixed
by **scoping fixtures**, not by deleting tests.

---

## 3. Paired-file overlap — the mirror rule's real cost

`CLAUDE.md` requires `black_bloc/x.py → tests/test_x.py` and
`black_bloc/cogs/**/x.py → tests/cogs/**/test_x.py`, which produces a
helper-module test file and a cog test file (and often an api one) per
feature. **36 such pairs exist.** The question is whether they assert the same
thing twice.

### 3.1 The pairs, by size

| Feature | helper `tests/*.py` | cog `tests/cogs/**` | api `tests/api/tools/**` | Exact same-name tests |
|---|---:|---:|---:|---:|
| tempvoice | 171 | 162 | 37 | 0 |
| polls | 94 | 159 | 37 | 2 |
| chat | 129 | 98 | 45 | 1 |
| role menus | 38 | 133 | 69 | 1 |
| requests | 99 | 90 | 56 | 1 |
| applications | 57 | 85 | 58 | 1 |
| raid trains | 66 | 83 | 40 | 1 |
| pings | 65 | 176 | 22 | 1 |
| golive · youtube · events · birthdays · modmail · automod · honeypot · modcases · chat-memory · presence · selftest | — | — | — | **0 each** |

```
# AST comparison of every tests/*.py against same-named files under
# tests/cogs/** and tests/api/**, then set-intersection of function names.
# 36 pairs; 8 exact name collisions in total.
```

### 3.2 Every same-name collision, read and judged

| # | Test name (both files) | Verdict |
|---|---|---|
| 1 | `test_a_number_is_read_off_a_card_with_or_without_the_hash` — `tests/test_applications.py` vs `tests/cogs/community/test_applications.py` | 🔴 **TRUE OVERLAP.** Both call the same pure `application_id_from` and assert the same outcomes; the cog copy is a strict **subset** (3 of the helper's 7 cases) and touches no panel, no cog and no interaction. Nothing in the cog copy is unreachable from the helper one. **The only genuine duplicate found in the suite.** |
| 2 | `test_a_new_intent_cannot_take_a_built_in_name` — helper vs `api/tools/test_chat.py` | Not redundant. Helper proves `clean_name()` raises `ChatError`; api proves the route turns that into **400 with the words a person reads**. Different layer, different assertion. |
| 3 | `test_setup_makes_the_events_role_and_points_both_feeds_at_it` — helper vs `api/tools/test_pings.py` | Not redundant. Helper asserts the role, the menu, the option label and emoji, and log kind `pings.setup`; api asserts the HTTP payload and log kind **`web.pings.setup`** — a *different row*, which is checklist item 34's guard. |
| 4 | `test_staff_can_still_post_a_poll_they_denied` — helper vs `cogs/community/test_polls.py` | Not redundant. Helper asserts the transition table permits `DENIED → OPEN`; cog drives the deny modal, presses **Post it anyway**, and asserts the poll was posted **and the member was DM'd**. |
| 5 | `test_yes_no_and_rating_write_their_own_answers` — helper vs cog | Not redundant, but thin. Helper asserts `options_for()` returns the lists; cog asserts the **posted Discord poll object** carries them — i.e. the cog actually passes them through. |
| 6 | `test_a_one_slot_train_is_never_offered_a_swap` — helper vs `cogs/content/test_raidtrain.py` | Not redundant, **thinnest of the set**. Both assert the same absent label; the cog version's only addition is that the *rendered view* omits it. |
| 7 | `test_the_unassigned_column_asks_for_assignee_none` — helper vs `api/tools/test_requests.py` | Not redundant. Helper proves the `list_requests`/`count_requests` filter; api proves the query string **`?assignee=none`** maps onto it and the JSON shape is right. |
| 8 | `test_taking_roles_back_renders_only_when_they_hold_one` — helper vs `cogs/community/test_role_menus.py` | Not redundant. Helper covers 3 input combinations of the pure button table; cog proves the **select-driven re-render** reaches two of them live. |

### 3.3 The near-name candidates — all five read, all five kept

`test_a_menu_with_a_clock_asks_how_long_…` (0.93 similar),
`test_a_second_start_…refused…bare_status` (0.92),
`test_no_row_on_a_…card_carries_more_than_five_controls` (0.88),
`test_unblock_is_…_somebody_is_picked` (0.86),
`test_moving_a_row_to_where_it_already_is_says_so…` (0.83).

**Every one is the same split and none is redundant:** the helper test proves
the pure table or function; the partner drives the real panel or route and
asserts something the helper *cannot see* — a row written to the database, a
**409 status code**, a modal submitted, a select re-rendered.

⚠️ **The clearest illustration is the tempvoice pair the mirror rule is most
often blamed for.** `tests/test_tempvoice.py::test_every_state_renders_exactly_its_row_of_the_table`
(160 ids) asserts the contents of the button table.
`tests/cogs/community/test_tempvoice.py::test_every_state_renders_exactly_its_row_of_the_button_table`
(20 ids) asserts `said == wanted`, where `wanted` is computed **by calling
`voice.card_buttons()` itself**. It re-asserts nothing; it proves **the panel
calls the table**. Deleting it would not remove a duplicated assertion — it
would remove the only proof that the two are connected.

🔴 **Finding: of 36 mirrored pairs and 5188 tests, exactly ONE test is a true
duplicate** (`test_a_number_is_read_off_a_card_with_or_without_the_hash` in
`tests/cogs/community/test_applications.py`). Deleting it saves **~62 ms.**

---

## 4. Parametrised tables

130 parametrised functions produce **1375 ids**; the other **3813** ids come
from unparametrised functions. The four largest tables account for 624 of the
1375.

| Table | ids | **Measured time, alone** | ms/id | Why |
|---|---:|---:|---:|---|
| `tests/test_settings_panel.py::test_every_registry_key_resolves_to_exactly_one_control` | 187 | **0.17 s** | 0.9 | Pure. No fixture. |
| `tests/test_tempvoice.py::test_every_state_renders_exactly_its_row_of_the_table` | 160 | **0.17 s** | 1.1 | Pure. No fixture. |
| `tests/api/test_contract.py::test_every_route_answers_with_the_keys_the_pages_read` | 149 | **63.31 s** | **425** | The `seeded` fixture, §2.2 — **rebuilt per id.** |
| `tests/cogs/content/test_pings.py::test_every_state_renders_exactly_its_row_of_the_button_table` | 128 | **9.23 s** | 72 | The per-cog `db` fixture — a fresh schema-v32 database per id. |

```
pytest -q -p no:cacheprovider "tests/test_settings_panel.py::test_every_registry_key_resolves_to_exactly_one_control"   # 187 passed in 0.17s
pytest -q -p no:cacheprovider "tests/test_tempvoice.py::test_every_state_renders_exactly_its_row_of_the_table"          # 160 passed in 0.17s
pytest -q -p no:cacheprovider "tests/api/test_contract.py::test_every_route_answers_with_the_keys_the_pages_read"       # 149 passed in 63.31s
pytest -q -p no:cacheprovider "tests/cogs/content/test_pings.py::test_every_state_renders_exactly_its_row_of_the_button_table"  # 128 passed in 9.23s
```

**Plainly:**

- **Collapsing the two pure tables would save nothing.** 347 ids cost **0.34 s
  between them** — 0.4 % of the suite's wall clock. Merging them into two
  looping tests would save roughly a third of a second and would cost the
  per-row failure message: today a broken registry key fails as
  `…[golive_ping_role_id]` and names itself. That is a bad trade at any price,
  and at 0.34 s it is not a trade at all.
- ⚠️ **Collapsing the other two WOULD save real time — but for a reason that
  has nothing to do with parametrisation.** Their cost is the **fixture built
  per id**, not the assertions. So the saving is available *without collapsing
  anything*: scope the fixture instead, keep all 277 ids and all 277 failure
  messages. Collapsing is the worse half of the same win.
- The parametrised ids are **not** where the suite's bulk is: 1375 of 5188.
  The other 3813 are hand-written one-offs.

---

## 5. Dead-weight candidates

| Candidate | Count | Detail |
|---|---:|---|
| `@pytest.mark.skip` / `xfail` | **0** | No test in the tree carries either decorator. |
| Skipped or xfailed at run time | **0** | `-rsx` on the full run printed no skip/xfail summary; the result line is a bare `5188 passed`. |
| Deselected | 59 | `tests/live/` (3 files), by `addopts = "-m 'not live'"` in `pyproject.toml`. **By design, not dead** — they hit the deployed api and need `BLACK_BLOC_LIVE_URL` + `BLACK_BLOC_LIVE_TOKEN`. |
| Only assertion is `assert True` | **0** | — |
| **No assertion of any kind** | **3** | `tests/cogs/community/test_requests.py::test_a_view_with_no_message_yet_does_nothing_on_timeout` · `tests/test_command_errors.py::test_install_is_a_no_op_without_a_tree` · `tests/test_groq.py::test_closing_a_client_that_never_opened_a_session_is_quiet`. ⚠️ **All three are "does not raise" tests** — the name states the contract and the absence of an exception is the assertion. They are legitimate, if better written with an explicit `assert`. |
| Verbatim-identical function bodies | 8 groups, **23 extra copies** | ⚠️ **All 23 are FALSE POSITIVES.** Every group is a `test_every_<x>_route_needs_a_session` / `…refuses_a_non_staff_visitor` pair whose body is identical but whose `@pytest.mark.parametrize` decorator supplies a **different route table** per feature. The bodies match; the tests do not. |
| **True verbatim duplicates** | **0** | — |
| True behavioural duplicates | **1** | §3.2 row 1, worth ~62 ms. |

```
# AST scan over all 102 files under tests/: decorators, assertions, and a
# sha256 of each function body with the name stripped.
# 3955 test functions; 0 skip/xfail decorators; 0 `assert True`; 3 assertionless.
```

One near-duplicate worth naming, though it is not dead weight:
`tests/test_chat.py` has three tests whose body is identically
`assert classify(text) == intent` over three separate 5–24 row tables
(`test_classify_reads_each_intent`, `test_the_data_and_route_phrases_land_on_their_own_intents`,
`test_asking_who_does_not_swallow_the_questions_that_came_first`). Merging
them into one table would remove two function definitions and save **0 s** —
the tables are split for readability and the ids are unchanged.

---

## What the numbers say

1. **The size is not the problem. The fixture scope is.** 84 % of the suite's
   time is `setup`; the assertions themselves are 13 %.
2. **Biggest lever, measured: `tests/api/test_contract.py`.** 153 tests (3 %)
   cost **14.7 s of the 79.1 s wall clock** — `-n auto` runs in **64.40 s**
   with the file ignored. Its 149 assertions cost **0.78 s**; its `seeded`
   fixture costs **65 s**. Seeding once per module instead of once per route
   recovers nearly all of it and **loses no coverage at all.**
3. **Second lever: the function-scoped `Database.connect()`.** 3298 tests each
   build a fresh schema-v32 SQLite file at **51 ms** — **168 s of CPU** spent
   creating identical databases. Nothing else in the suite is this large.
4. **Third lever: `create_app()` + `TestClient` at 84 ms**, rebuilt for each
   of 1035 api tests — **86 s of CPU**.
5. **Deleting tests is the worst available lever.** The one true duplicate in
   5188 tests is worth **62 ms**. The two biggest parametrised tables — 347
   ids, the ones that *look* like bloat — cost **0.34 s between them.**
6. **The mirror rule is not generating redundancy.** 36 paired files produced
   8 same-name tests, of which 7 prove a different layer. The cog test that
   computes its expectation by *calling* the pure table is the pattern, and it
   is the right one.
7. **There is no fat tail to trim.** The bottom 90 % of tests carry 66 % of the
   time, at 50–250 ms each — and almost all of that is fixture setup they all
   share.
8. **So: keep the 5188.** They are cheap per assertion, they are not
   duplicated, and none is skipped or empty. **Fix the three fixtures instead**
   — the arithmetic says that is worth ~250 s of CPU and ~15 s of wall clock,
   against ~62 ms available from deletion.

---

## Decisions for the owner

Each is a single yes/no. **Nothing below has been done.**

1. **Scope `test_contract.py`'s `seeded` fixture to the module** (seed once,
   run all 149 routes against it) — **saves ~14.7 s of the 79.1 s wall clock,
   measured.** Trades: the 149 routes stop being independent, so a route that
   writes state could affect a later one; the file's own comment ("every
   contract entry runs against a fresh seed") was a deliberate choice. Coverage
   lost: **none.** Yes / no?
2. **Make the `db` fixture session- or module-scoped** (build schema v32 once,
   roll back or truncate per test) across the 46 files that use it — **frees up
   to ~168 s of CPU.** Trades: real work in 46 files; tests stop being
   isolated-by-construction and rely on a reset that must itself be correct.
   Coverage lost: **none.** Yes / no?
3. **Make the api `client` / `create_app()` fixture module-scoped** — **frees up
   to ~86 s of CPU** across 1035 tests. Trades: the app is shared inside a
   module, so a test that mutates app state leaks. Coverage lost: **none.**
   Yes / no?
4. **Delete `tests/cogs/community/test_applications.py::test_a_number_is_read_off_a_card_with_or_without_the_hash`** —
   the one true duplicate. **Saves ~62 ms.** Coverage lost: **none** (it is a
   strict subset of the helper test). Yes / no?
5. **Give the three assertionless tests an explicit assertion** (§5) rather
   than relying on "did not raise". **Saves 0 s.** Trades: nothing but the
   edit. Coverage lost: none; coverage *clarity* gained. Yes / no?
6. **Leave every parametrised table as it is.** Collapsing the four biggest
   would save **~0.34 s** on the two pure ones and would cost per-row failure
   messages on all four. Recommended: **yes, leave them.** Yes / no?
7. **Leave the mirror rule and all 36 paired files alone.** The measured true
   overlap is one test. Recommended: **yes, leave it.** Yes / no?
