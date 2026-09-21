# Self-test — the bot proves itself against the real guild, then cleans up after itself

> **Audience:** the build agent and the reviewer; the owner for §A and §H. **Status:** TRACKED ·
> ✅ **SHIPPED 2026-09-05 as v86** (merge of `worktree-agent-a4aa5efd43f249ba6`; sweeps 252–261; schema
> 30 → 31; deviations in the `## Build deviations` foot — read C.2 (18 panels, not 29), C.3 (route table,
> not the contract) and B (the operator token reads but never starts). ✅ **Run by a person** — the owner
> ran it from `/settings` ▸ **Self-test…** (sweep row 252, recorded on `../TODO.md`'s v93 line); the line
> here saying "not yet run by a person" stood until 2026-09-11.
> 🔧 DESIGN 2026-09-05 14:05. Owner ask 13:52, verbatim: *"test it all, can we build
> api test and endpoints"*; owner decision 14:02, verbatim: *"do a but after 5 minutes purge the
> discord chat of all test, keep the logs on the website tho under test"* — (a) of the three readings
> offered (see `TODO.md`), plus the purge and the website's Test view, which are §D and §F here.
> **Last verified: 2026-09-11 09:15** — docs-wide staleness pass against **v108** `73e2e44`.
> **Re-measured:** the live boot line has said **107 ok, 0 failed, 24 messages posted** at every boot
> from v90 onward (16 consecutive deploy records on `../deploys.log`) — this file's cost table said
> **106**, the v86 figure, and was one behind from the moment the personality-pool check landed at v90.
> **FIXED:** that table now carries the `pool.*` family and totals **107**; §A still said the cards are
> deleted "five minutes later" when the default has been **1 minute** since v103 (the rest of the file
> already said so). ⚠️ **NOT re-checked:** the per-family split (35 / 18 / 47 / 6) was not re-derived
> by import — only the total is measured, from the boot line; schema is **34** now, not the 30/31 the
> line-anchor list below was read against; and nothing here met Discord or a browser today.
> Before that, **2026-09-05** — the paths below were READ against `main` at **`6bf6a48`**:
> `black_bloc/actionlog.py` (`log_action` at :107), `black_bloc/logkinds.py` (`FEATURES` :24,
> `HEADS` :44, `feature_of` :373, `should_post` :404, `log_level_key` :427), `black_bloc/guard.py`
> (`test_channel_id`, `allows_channel` :60), `black_bloc/api/server.py` (25 routers, :143–165),
> `black_bloc/api/status.py` (`/api/status` :382, `/api/actions` :416, `kinds_present` :243),
> `black_bloc/config.py` (`test_mode` :67, `test_channel_id` :68), `black_bloc/storage/db.py`
> (`SCHEMA_VERSION = 30` :11), `site/public/audit.html` (the Logs page), `site/public/health.html`,
> `tests/api/test_contract.py`. Line numbers drift; trust the anchor text.

## A. What it is, in one paragraph (owner)

**Run the self-test** makes the bot exercise itself, live, without a person: inside the running bot,
against the REAL guild, it opens every panel the way a command would, posts each one's first card into
the test channel as a real message, runs every read the website's pages make, and checks that every
channel and role the settings point at still exists with the permissions that feature needs there. Each
check writes one line to the log. **A minute later the bot deletes every message the test posted**
(`selftest_purge_minutes`, default **1** since v103 — it was five until 2026-09-10),
so Discord stays clean; **the log lines stay on the website under a "Test" view**, out of the way of the
real logs. ~~It runs at every boot (so every deploy proves itself in the Fly log without anyone opening
Discord)~~ — **REVERSED 2026-09-20 (§K, branch `selftest-boot`): it runs at every boot only while
`TEST_MODE` is on.** With test mode off, a live server was being given eighteen panel cards at every
deploy, which is what the owner asked to stop; `selftest_on_boot` still says otherwise either way.
Staff can run it on demand from **`/test`**, from `/settings` ▸ **Self-test…**, or from the website's
Health page.

What it cannot do — said once, honestly: **no API can click a Discord button.** Discord originates
interactions; the bot can only answer them. Button, select and modal handlers stay proven by the
pytest fakes (5002 tests). The self-test proves everything up to and including the card being posted;
only the *look* of a card in the Discord client still needs eyes.

## B. Doors (all of them call ONE function — `selftest.run(bot, guild, *, actor, via, channel, keep_minutes)`)

⚠️ **FOUR doors since 2026-09-20 (§K)** — `/test` was added as a fourth, on the same function.

| Door | Who | Where |
|---|---|---|
| Boot | the bot itself | `bot.py` lifecycle: after `database ready` + `synced N`, when `selftest_on_boot` is on. Logs ONE line: `selftest: <ok> ok, <failed> failed, <n> messages posted (purge in <m> min)` and one `selftest: FAILED <check> — <sentence>` line per failure. This line is what the conductor reads with `flyctl logs` to verify a deploy. |
| Discord | staff | `/settings` ▸ **Run the self-test** — a button on the settings panel's root card (Build 2's `MoveButton` pattern, `black_bloc/cogs/core.py`). Ephemeral answer in words: the counts, and the failures by name. ~~**No new command** — the tree stays at 29, zero Groups~~ — **REVERSED 2026-09-20 (§K): the owner asked for `/test` by name**, so there IS a new command and the tree is **33**, still zero Groups (`tests/test_bot.py:TOP_LEVEL_NOW` pins it). The button stays; both press the same function. |
| Discord (`/test`) | staff | `/test` in `cogs/core.py`, added 2026-09-20 (§K). Optional `where` (a channel, for this run only) and `keep` (1–1440 minutes, for this run only); staff-gated exactly as `/settings` is. |
| Website | staff | `POST /api/selftest` starts a run and returns `{run_id, started_at}`; `GET /api/selftest` lists the last 20 runs (`run_id, started_at, finished_at, ok, failed, posted, purged_at, via, actor`); `GET /api/selftest/{run_id}` returns the run with its checks (`name, feature, ok, detail, at`). Operator token allowed (it is a staff read/write like the rest of `status.py`). |

A run that is already going refuses a second start **in words**: "A self-test is already running (started
14:03, 12 of 41 checks done)" — never a bare 409 (global rule: no bare HTTP status).

## C. Checks (the registry: `black_bloc/selftest.py`, `CHECKS: list[Check]`)

`Check(name, feature, run)` where `run(bot, guild, actor) -> str` returns the one-sentence detail on
success and raises on failure; the runner turns the exception into the failure sentence (class + message,
no traceback in the row — the traceback goes to the Fly log at WARNING). Four families, in this order:

1. **`config.<key>`** — for every settings key of type channel/role (the registry in `settings_store.py`
   knows which; use its type table, do NOT hand-list keys): the id resolves in the guild, and for a
   channel the bot has the permissions that feature's poster needs there (`view_channel`, `send_messages`,
   `embed_links`; plus `manage_messages` for keys whose feature deletes — honeypot, automod, mod). An
   UNSET key is `ok` with detail "not set" (unset is a state, not a fault).
2. **`panel.<command>`** — for every one of the 29 commands that opens a panel: build the root card the
   way the command handler does (embed + view), against the real guild, with the actor as the member;
   then **post it as a real message** into the self-test channel (§D) with the view attached. The detail
   is `"posted; N buttons, M selects"`. ⚠️ Build the card through the SAME function the command handler
   calls — never a copy. Where a handler builds inline today, extract `root_card(bot, guild, member)` in
   that cog (a refactor with tests, not a rewrite). Panels whose root needs a target (a ticket, a
   request, a poll) render their **empty/none state** — that is the state a person would see with
   nothing selected, and it is a real card.
3. **`read.<page>`** — for every website page's `GET` routes (the contract test knows the list; reuse
   its route inventory, do not hand-list): call the route function in-process through the FastAPI app
   with a staff session (as `tests/api/conftest.py` does, but against the LIVE db) and require 200 and
   the documented shape (top-level keys). Read-only routes only; no writes.
4. **`send.<feature>`** — for features that post on their own schedule (go-live, YouTube, birthdays,
   events, pings, raidtrain): render the announcement embed for a synthetic record marked `selftest`
   and post it into the self-test channel. Not the feature's real channel — §D.

The runner does not stop on failure; every check runs; the run's `ok`/`failed` counts are the totals.

## D. The five-minute purge (owner's words: "after 5 minutes purge the discord chat of all test")

- **Every message the test posts goes into ONE channel:** `selftest_channel_id` (settings key,
  channel type, default = `TEST_CHANNEL_ID` from config while TEST_MODE is on; after the lift it is
  whatever staff point it at, and while TEST_MODE is on the guard refuses any other channel anyway).
- Each posted message id is written to a new table **`selftest_messages(run_id, channel_id, message_id,
  posted_at)`** BEFORE the next check runs — one write, one row (checklist 34) — so a restart mid-run
  still knows what to delete.
- A `discord.ext.tasks` loop (`purge_loop`, every 60 s) deletes every row whose `posted_at` is older
  than `selftest_purge_minutes` (settings key, int minutes, default **1** — was 5 until 2026-09-10, when the owner said "the test stuff posted each deployment should last 60s instead since it's mainly for you and not me"; the loop ticks every 60 s so a 1-minute setting purges within 60–120 s — min 1, max 1440) with
  `channel.delete_messages` in chunks of 100; messages older than 14 days fall back to one-by-one
  `message.delete()`; a message already gone (404) counts as purged. Purged rows are deleted from the
  table and the run's `purged_at` is stamped when its last message goes. The purge writes ONE log row
  per run: `selftest.purged` with `{"messages": n}`.
- **On boot the loop's first tick runs immediately**, so leftovers from a run that died mid-way are
  purged before the boot self-test posts new ones.
- Staff can purge NOW: `/settings` ▸ the self-test card's **Purge now** button, and `POST
  /api/selftest/{run_id}/purge`.

## E. Logging — the "Test" feature (owner's words: "keep the logs on the website tho under test")

- New feature **`selftest`** in `logkinds.FEATURES` and `HEADS` (`"selftest": "selftest"`), shown as
  **Test** wherever features are named to a person (`FEATURE_WORDS`/labels — find the one table).
- Kinds: `selftest.started`, `selftest.check` (details: `name, feature, ok, detail, run_id`),
  `selftest.finished` (details: `ok, failed, posted, run_id`), `selftest.purged`. Via travels as every
  other kind's does (`kind_via`, `via_of`): the website door writes `web.selftest.*`, the boot door's
  details carry `"via": "boot"` — add `boot` to `VIA_WORDS` ("by the bot at boot").
- **Log level for `selftest` defaults to `off`** (`log_level_key("selftest")`, registry entry like the
  other 17 features) — the rows are in the database and on the website, but nothing is posted to the
  staff log channel unless staff turn it up. Configurable both ways (checklist 33).
- **The Logs page's default view EXCLUDES the Test feature** — `/api/actions` with no `feature` filter
  adds `AND kind NOT LIKE 'selftest.%' AND kind NOT LIKE 'web.selftest.%'`; choosing **Test** in the
  feature filter shows only those rows. One place decides this (`actionlog.feature_clause` or a sibling);
  the CSV export follows the same rule. The Requests page's Logs card and every per-feature Logs card
  are unaffected (they filter by their own feature already).

## F. Website surfaces (one fact, one home)

- **Health page (`health.html`, `/api/status`)** owns "is the bot well?" — add a **Self-test** card:
  last run's started/finished, `ok`/`failed`/`posted`, whether it is purged yet, the failures by name
  with their sentence, and a **Run the self-test** button (staff; refuses in words when a run is going).
  The card polls `GET /api/selftest` every 15 s while a run is unfinished.
- **Logs page (`audit.html`)** owns the rows — the **Test** filter entry from §E; nothing else new.
- Mock: `site/mock/server.mjs` gains the three `/api/selftest` routes and the new feature in its
  actions; `node site/mock/check.mjs` must pass with the new route count stated in the report.

## G. Settings keys (registry, `settings_store.py`; group **core**, like the panel-minutes keys)

| key | type | default | words |
|---|---|---|---|
| `selftest_on_boot` | bool | ~~true~~ **`TEST_MODE`** (changed 2026-09-20, §K) | Whether the bot runs the self-test at every boot |
| `selftest_channel_id` | channel | `TEST_CHANNEL_ID` | Where the self-test posts its cards |
| `selftest_purge_minutes` | int 1–1440 | 1 (was 5 until 2026-09-10) | How long the self-test's messages stay before the bot deletes them |
| `log_level_selftest` (via `log_level_key`) | level | off | as the other features |

Reachable from `/settings` ▸ **Panels & commands…** (or wherever Build 2 put the core group's siblings)
AND the website's Settings page under **core** — the settings panel's `reachable_on_the_panel` test
must still hold.

## H. `tests/live/` — the second half of the owner's ask ("api test")

A pytest package **`tests/live/`** that hits the DEPLOYED api (`https://blackbloc.heygabi.ai`), skipped
whole unless both env names are set: `BLACK_BLOC_LIVE_URL` and `BLACK_BLOC_LIVE_TOKEN` (the operator
token — NAME only in docs, never the value; the owner mints it with `scripts/mint-operator-token.ps1`).
Marked `@pytest.mark.live`; excluded from the default `pytest` run by `pyproject.toml`
(`-m "not live"`) so the 5002 stay hermetic; run with `pytest -m live tests/live`.

- `test_reads.py` — every GET route the contract inventory lists answers 200 with its top-level keys.
- `test_selftest.py` — `POST /api/selftest`, poll `GET /api/selftest/{run_id}` until `finished_at`, assert
  `failed == 0`, then `POST …/purge` and assert `purged_at`. This is the one live test that exercises
  Discord, through the bot, with cleanup.
- `test_refusals.py` — no token → refused in words (json `message`), never a bare status body.

No live WRITE test touches a real feature record (birthdays, polls, …); the self-test run is the
sanctioned write path. Document the run command in `docs/access/testing.md` (create it if there is no
testing runbook; check `access/README.md` first).

## I. Rules the build carries (all standing; listed so none is missed)

- TEST_MODE stays as it is; the self-test posts ONLY in `selftest_channel_id`, which the guard already
  limits to `TEST_CHANNEL_ID`/DMs while TEST_MODE is on. Never post to any feature's real channel.
- Near-zero comments; explanations go to `docs/info/code-notes.md` keyed `path:name`, appended under a
  `# Self-test (wave 5)` head. One-line docstrings at most.
- Tests mirror the package: `black_bloc/selftest.py` → `tests/test_selftest.py`; new API module
  `black_bloc/api/selftest_api.py` → `tests/api/test_selftest_api.py`; `tests/live/` is the one
  deliberate exception (it mirrors no module — say so in its `__init__.py` docstring).
- Schema **30 → 31** (`selftest_runs`, `selftest_messages`), migrate-before-deploy is already the
  deploy script's job.
- Review checklist `docs/info/review-checklist.md`, all 34 items; 33 (configurable both ways) and 34 (one
  write, one row) are the ones this design leans on.
- Sweep rows lettered **`ST1`–`STn`** at the foot of `docs/access/sweeps.md`; the conductor numbers
  them at the merge (after the modmail follow-up's `ML` rows).
- Report carries: measured test count, ruff clean, mock route count, the tree still 29 / zero Groups,
  and what was NOT verified (no boot, no token, no Discord — the conductor does those at the landing).

## J. Forks the conductor decided (owner: "don't wait for me")

- **F-ST1 — does the boot run post messages?** (a) yes, same as any run, purged after 5 min — chosen:
  the owner asked for the chat to be purged, not for the boot run to be silent, and a boot that posts
  nothing proves nothing about sending. (b) boot run renders only. Rejected.
- **F-ST2 — where does "Run the self-test" live on the website?** (a) Health page — chosen, it owns
  wellness. (b) Settings page. Rejected: Settings owns values, not actions.
- **F-ST3 — `panel.*` checks post with live views?** (a) yes, buttons are real and work for the 5
  minutes — chosen; a card with a dead view is not the card a person sees. Panels time out on their own
  `*_panel_minutes` as usual. (b) strip the view. Rejected.

## Build deviations

> Written by the build on `worktree-agent-a4aa5efd43f249ba6`, 2026-09-05, off `main` at `374b498`.
> All three forks were built as chosen. Measured, not predicted: **5090** tests pass (`pytest -q -n
> auto`), `ruff check .` is clean, `node site/mock/check.mjs` reports **17 pages / 149 routes**,
> the tree is **29 top-level commands with ZERO Groups**, and `SCHEMA_VERSION` is **31**.
> ⚠️ **NOT verified:** no boot, no token, no Discord — nothing here has run against the live bot.

| § | The design said | The build did, and why |
|---|---|---|
| C | `Check(name, feature, run)` where `run(bot, guild, actor) -> str` | `run(one: Run) -> str`. A check has to write a posted message id down against the RUN before the next check goes (§D), so it needs the run id and the poster, not three loose arguments. `Run` carries bot, guild, actor, via, run_id and `post()`. |
| C.1 | "for every settings key of type channel/role" | Exactly that — **35 checks**, read off `KEY_TYPES` with no hand-listing. `manage_messages` is added for keys whose namespace is `honeypot` or `automod` (which is where `modlog_channel_id` lands, by `NAMESPACE_OVERRIDE`). |
| C.2 | "every one of the **29** commands that opens a panel" | **18.** The tree is 29 commands; 18 open a panel and 11 take an argument and act or answer one line. ⚠️ **No `root_card` extraction was needed** — all 18 already had a module-level builder, and an AST test proves each command's own module calls the one the table names. |
| C.3 | "the contract test knows the list; reuse its route inventory" | ⚠️ **Could not be done, and should not be.** `site/mock/contract.json` **is not in the Docker image** (`Dockerfile` copies `black_bloc` and `site/public` only), so a runtime read of it would pass locally and fail on Fly. The family walks the running FastAPI app's own route table instead — **47 checks** — which is also the better single home. The contract inventory IS used by `tests/live/test_reads.py`, which runs from the repo. |
| C.3 | "require 200 and the documented shape (top-level keys)" | 200 and a body that is not `None` and not an empty object. With `contract.json` out of reach there is nothing to check keys against; the detail records the top-level keys it found, so a changed shape is visible in the log even though it does not fail. An empty LIST passes — a guild with no birthdays is not a fault. |
| C.4 | six `send.<feature>` checks | Built, all six, each through the feature's OWN renderer. ⚠️ `send.pings` posts a ping **prefix**, not a card: ping roles never post anything of their own, and the prefix is the honest shape of what that feature contributes. |
| B/G | **Run the self-test** and **Purge now** on the settings ROOT card | On a **Self-test…** CARD one press in. Row 2 of the root is already at Discord's five-control limit, and the feature needed a **Logs** button anyway (adding `selftest` to `FEATURES` makes `tests/test_bot.py` demand a `send_logs` call site). Same moves, plus room for the state the card has to show. |
| B | "Operator token allowed (it is a staff read/write)" | ⚠️ **Half true, and the design could not have known.** `auth.py:operator_session` refuses every method but `GET`/`HEAD` in words, so the token reads the three GETs and **cannot start a run**. `tests/live/test_selftest.py` asserts that refusal, and the start → poll → purge test takes an optional staff session cookie (`BLACK_BLOC_LIVE_SESSION`) instead. Recorded in `docs/access/testing.md`. |
| E | `HEADS` gains `"selftest": "selftest"`, shown as **Test** | Done, plus `FEATURE_PAGES["selftest"] = "health.html"` and all four kinds added to `ROUTINE` — without that, `selftest.purged` matches an `IMPORTANT_SUFFIXES` entry and the Logs page's Important switch fills with test rows. |
| F | three `/api/selftest` routes in the mock | **Four** (the purge is a fourth), and **three** contract entries. ⚠️ `POST /api/selftest` is deliberately NOT in `contract.json`: it starts a real run against the live guild, which is the one route neither fixture can exercise without posting into Discord. `tests/live` proves that one. |
| — | not in the design | ⚠️ **A defect found and fixed:** an `/api` path nothing served answered Starlette's bare `{"detail": "Not Found"}`. The global no-bare-status rule forbids it and the MOCK had been answering it in words for months. `server.py:unknown_route` now answers a sentence; a route's own `Refused(404, …)` keeps its own words. |

### What the run actually costs, measured

| Family | Checks | Messages posted |
|---|---|---|
| `config.*` | 35 | 0 |
| `panel.*` | 18 | 18 |
| `read.*` | 47 | 0 |
| `send.*` | 6 | 6 |
| `pool.*` | 1 | 0 |
| **total** | **107** | **24** |

⚠️ The `read.*` count moves with the API: it is derived, so adding a GET route adds a check.
⚠️ **The total was 106 at the v86 landing and has been 107 since v90**, when the personality pool's
`pool.in_step_with_gabi` check landed (`personality-pool-design.md`). The measured total is the boot
line on `../deploys.log` — `selftest: 107 ok, 0 failed, 24 messages posted` — not this table; the
per-family split above is the v86 reading and was NOT re-derived on 2026-09-11.

## K. 2026-09-20 — the boot run follows test mode, and `/test` for staff (owner ask, PRIORITY)

Owner, 2026-09-20 17:3x, verbatim: *"i think now that we're no longer in test mode, we don't need to have black bloc post every
panel in logs. Let's leave that as a default when in test mode and then a /test command that spews out all the panels for staff
only. PRIORITY TASK"*. Measured: `selftest_on_boot` defaults `true` regardless of `TEST_MODE` (§G), so since the lift every boot
still posts the 18 cards into `#blackbloc-logs` and purges them a minute later — that is the "every panel in logs".

**K.1 The default follows test mode.** `settings_store.py:Store.default` gains a branch: `selftest_on_boot` → `self.settings.test_mode`
(`SELFTEST_ON_BOOT_DEFAULT` goes; the `KEY_HELP` sentence says "the default is on while test mode is on and off otherwise"). The key
stays a bool in group **core**, so either way is one change on the Settings page or `/settings set-value` (configurable both ways).
`runs_on_boot` is unchanged — it reads the key. The mock server's `SETTING_SPECS` row and `labels.js` follow. ⚠️ An explicit stored
`true` still wins: the conductor clears any stored row after the deploy (`DELETE /api/settings/selftest_on_boot`), the build does not
touch data.

**K.2 `/test` — a fourth door, staff only.** The owner named the command, so the minimise-slash rule yields for this one; it is the
same function as the other three (`selftest.run(bot, guild, actor=…, via=VIA_DISCORD)`), never a fourth path. Shape:

| | |
|---|---|
| command | `/test` in `cogs/core.py` beside the settings command; `default_member_permissions` as the other staff commands; the staff gate the way `/settings` gates (refused in words, ephemeral) |
| `where` (optional channel) | the channel the cards are posted in for THIS run; default = the self-test channel (`selftest_channel_id`, unset → the test channel). `selftest.run` takes an optional `channel` that overrides the resolved one for that run only — the purge finds the messages by the stored ids, not by channel, so purging is unchanged |
| `keep` (optional int, minutes, 1–1440) | how long the cards stay before the purge for THIS run; default = `selftest_purge_minutes`; the run's `purge_at` is computed from it (`Run` gains the field or the row does — the builder picks, and says which) |
| the answer | ephemeral, in words: "Self-test done — 18 ok, 0 failed, 18 cards in #channel, gone in 10 minutes"; a busy run answers `BUSY` as today; no channel answers `NO_CHANNEL` |
| logs | `selftest.started` / `selftest.finished` as today with `via: discord` and the actor; `where`/`keep` land in `details` when given |

**K.3 Tests.** `tests/test_selftest.py` (default follows `test_mode` both ways; `run` honours a channel override and a keep override;
the purge still finds an overridden run's messages), `tests/cogs/test_core.py` (`/test` exists, is staff-gated, passes the two
options through, answers in words), the command-tree count guard (+1, the `zero Groups` assertion holds), `tests/test_settings_store.py`
(the default branch). Docs: `code-notes.md`; this section's foot gets a dated `### K deviations`; `access/testing.md`'s live-in-Discord
line names `/test`; `architecture.md` command count. NOT `TODO.md` / `DONE.md` / `deploys.log` / `KNOWN_ISSUES.md`.


### K deviations — 2026-09-20, branch `selftest-boot` off `main` `74c25bf`

Built as §K says, with four decisions the section left to the builder and one it did not foresee.
Measured, not predicted: **6818** tests pass (`pytest -n 8 -q`, and again with `BB_REVERSE=1`),
`ruff check .` is clean, `node site/mock/check.mjs` reports **20 pages / 186 routes / 24 core
settings**, and the tree is **33 top-level commands with ZERO Groups**.

| § | The design said | The build did, and why |
|---|---|---|
| K.1 | "`SELFTEST_ON_BOOT_DEFAULT` goes" | Gone, not flipped to `False`. `Store.default` reads `self.settings.test_mode` through `getattr(..., "test_mode", False)`, so a settings stand-in without the flag reads OFF — the safe side. The key is still a bool in group `core`, so an explicit stored `true` still wins on a live server, which is the conductor's `DELETE /api/settings/selftest_on_boot` step. |
| K.1 | "the mock server's `SETTING_SPECS` row and `labels.js` follow" | Both, and the mock row's VALUE moved from `true` to `false` as well as its default — the mock stands for a live server, and test mode is off. |
| K.2 | "the run's `purge_at` is computed from it (`Run` gains the field or the row does — the builder picks, and says which)" | ⚠️ **BOTH, and the row is the one that matters.** `Run.keep_minutes` alone would have been a bug: the purge is a 60-second loop in `cogs/core.py` that re-reads `selftest_messages` with no `Run` in hand, and the run object is gone the moment the run finishes. A `/test keep:60` would have been swept at the next tick by the global 1 minute. So **`selftest_runs.keep_minutes`** (schema **46 → 47**, added through `ADDED_COLUMNS`, NULL = use the setting) and `purge` computes its cutoff per row instead of once per sweep. Migrate-before-deploy already covers it. |
| K.2 | "the purge must still find the run's messages (it works from stored message ids — verify, do not assume)" | ⚠️ **Verified, and it does.** `selftest_messages` stores `channel_id` per message, and `purge` groups by the STORED channel, never by `selftest_channel()`. `test_the_purge_finds_an_overridden_runs_messages_by_the_ids_it_wrote_down` posts into the other channel and asserts the bulk delete lands there and not in the self-test channel. `waiting_messages` is now a LEFT JOIN onto `selftest_runs` so each row carries its run's `keep_minutes`; its `ORDER BY` had to become `m.id` because `id` was ambiguous after the join. |
| K.2 | "`keep` (optional int, minutes, 1–1440)" | NOT `app_commands.Range`. The bound is validated by `coerce_value(SELFTEST_PURGE_MINUTES, …)`, so the numbers live in the registry only and the refusal a person reads is the registry's own `KEY_MIN_REASON` sentence. `Range` would have refused it in Discord's words and put the bounds in a second place. |
| K.2 | "no channel answers `NO_CHANNEL`" | Answered **before** the run starts rather than as 24 failed checks. `/test` resolves `where or selftest_channel(...)` up front; `None` is one ephemeral sentence and no run row. The other three doors are untouched — `Run.post` still raises `CheckFailed(NO_CHANNEL)` per check as it always did. |
| K.2 | "the answer … 'Self-test done — 18 ok, 0 failed, 18 cards in #channel, gone in 10 minutes'" | Same facts, in the house wording of the existing `sp.SELFTEST_DONE`: `selftest.TEST_DONE` reads *"The self-test ran: **18 ok, 0 failed**, 18 card(s) posted in #blackbloc-logs. They are deleted again in 10 minute(s)."* The failure list under it is shared with the settings card (`cogs/core.selftest_body`), so the two doors cannot drift. |
| — | not in the design | The `/settings` ▸ **Run the self-test** button now reads its minutes through `selftest.minutes_of(bot, one)` rather than `purge_minutes(bot, guild.id)`. No behaviour change today (that door passes no `keep`), but it means one function answers "how long do THIS run's cards stay" for every door and for the boot line. |

### K — what was NOT verified

- ⚠️ **Nothing here has met Discord.** No `/test` has been typed, no card has been posted, no
  purge has deleted a real message, and no boot has happened with `TEST_MODE` off. Every claim
  above is the hermetic suite's, against fakes.
- ⚠️ **The migration has not run against the live database.** `selftest_runs.keep_minutes` is
  proven by `tests/storage/test_db.py` on a file whose column is dropped and re-added; the real
  `blackbloc.sqlite3` on Fly has not been touched.
- The 107-check figure was NOT re-derived — every new test stubs `checks_for` down to one or two
  checks, which is the house pattern. The real cost of a `/test` run is still the boot line's.
- No browser rendered the Settings page, so the changed `labels.js` sentence and the mock's new
  `selftest_on_boot` value were read, never seen.
- `/test` was not exercised through a real `app_commands` invocation — the tests call the
  callback directly, as every other command test in this repo does — so Discord's own option
  parsing of `where` (a `TextChannel`) and `keep` (an int) is unproven.
