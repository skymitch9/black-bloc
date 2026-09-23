# Testing — the hermetic suite, the mock, and the live api

> **Audience:** Claude sessions and the owner. **Status:** TRACKED — ⚠️ secret NAMES only.
> Last verified: **2026-09-22 23:2x — the hermetic suite's junit file, timeout and loopback plugin only** (branch
> `gate-names`): full suite **7,339 passed + 3 skipped in 43 s wall at `-n 16`**, twice, on that branch. Before that,
> **2026-09-19** — the docs staleness pass after the **TEST_MODE lift**
> (2026-09-18 16:08). What changed here: the fourth layer's *Needs* column said **"staff, in the
> test channel"** and there is no test channel any more — a self-test run now posts its cards
> into `selftest_channel_id`, which is `#blackbloc-logs` because that is where the key points,
> not because a guard forces it. The hermetic layer's figure is re-read off the **v141** gate
> (**6,757** passed + 3 skipped; it quoted 5,986 at v116). ⚠️ **NOTHING IN THIS FILE WAS RUN
> TODAY** — not `pytest`, not `ruff`, not the mock (`check.mjs` needs `server.mjs` listening),
> and not `tests/live/` (it needs `BLACK_BLOC_LIVE_TOKEN`, which this pass did not hold). The
> live-suite results below are all 2026-09-06 readings against v97–v99 and have **not** been
> re-run since; treat them as dated, not current. ⚠️ **One thing a future session should know:**
> `/api/youtube/status` was anonymously readable at the v139 boot and is **not** now — it
> answers `not_signed_in` (checked 2026-09-19), so `/health` is the only endpoint this suite's
> world can read without a cookie. Before that,
> **2026-09-11 08:37** — re-measured off `main` `1d090e5` (**v108 LIVE**):
> `pytest -q -n auto` = **5,546 passed** in **40.1 s** (was 5087 on 2026-09-05);
> `site/mock/contract.json` = **17 pages / 150 routes / 115 action kinds** (was 149 routes);
> `pytest -m live tests/live --co` = **59 collected**, unchanged. Also corrected below:
> `selftest_purge_minutes` defaults to **1**, not 5 (`settings_store.SELFTEST_PURGE_MINUTES_DEFAULT`
> — it was lowered on 2026-09-10). ⚠️ **NOT run today:** `tests/live/` (a worktree holds no token,
> so nothing reached the deployed host), the mock **server** (`node site/mock/check.mjs` needs
> `site/mock/server.mjs` listening on 8788 — the 17/150 figures were read straight out of
> `contract.json`, which is the file both halves read), and nothing met live Discord or a browser.
> Before that, **2026-09-05** — the counts were MEASURED on the wave-5 self-test branch
> (`pytest -q -n auto` = 5087 passed; `node site/mock/check.mjs` = 17 pages / 149 routes; `pytest
> -m live tests/live` = 59 collected, all skipped with neither env name set).
> **2026-09-06 13:55 — `tests/live/` ran against the deployed host for the first time** (v97,
> `OPERATOR_READ_TOKEN` set): **20 passed / 38 failed / 1 skipped** of 59 in 17 s. The 38 are the
> `test_every_read…` sweep hitting the operator guess bucket (30 a minute per IP, charged on GOOD tokens —
> a defect, on TODO for v98) plus one write-refusal test that meets the `cross_site` origin check before
> the operator gate; the skip is the selftest start (no `BLACK_BLOC_LIVE_SESSION`). Loop health, `/health`,
> the bot-in-guild check and every refusal test passed.
> **2026-09-06 14:24 — after v98: 58 passed / 1 skipped** of 59 in 16.5 s (the skip is still the selftest start
> without `BLACK_BLOC_LIVE_SESSION`). The 429s are gone (the bucket fix); 27 of the 38 turned out to be a
> THIRD, test-side defect fixed on `main` right after: `test_reads.py` read the contract's `keys` off the top
> level of every payload, ignoring `shape` (`list` / `map` / `namespaces`) the way `site/mock/check.mjs`
> honours it — `rows_of` now reads the same way; and `/api/requests/mine` refuses the operator identity
> with `403 not_a_member` in words, which is right (the operator is nobody's account), so the sweep accepts
> that one answer. **58 / 59 is the live suite's first green run.**
> **2026-09-06 20:02 — against v99 (operator read bound): 58 passed / 1 skipped**, unchanged — the design required
> the live suite not to change, since a 300-read flood against the deployed host is not a test for every push.
> That flood was drilled by hand instead (sweep row 322): 400 reads at once → 308 answered, 92 refused in words.

## The three layers, and what each one proves

| Layer | Command | Proves | Needs |
|---|---|---|---|
| Hermetic | `pytest -q -n auto` | every module, every route shape, every panel card, against fakes — **6,757 passed + 3 skipped** (2026-09-18, the v141 gate off `../deploys.log`; the 3 skips are where the voice-receive extension is absent — **KI-31**; it read 5,986 at the v116 gate) | nothing but the venv — ⚠️ and a CLEAN environment: a shell that exports the real `.env` names (`POLL_VOTE_SECRET`, `DEV_GUILD_ID`, `TWITCH_*`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`…) turns **nine** "no key" tests red; see `../info/gotchas.md` |
| Mock | `node site/mock/server.mjs` then `node site/mock/check.mjs` | the PAGES' half of the contract: the mock answers the same shapes the real routers do | node |
| Live | `pytest -m live tests/live` | the DEPLOYED host answers, the bot is connected, a self-test run really exercises Discord and cleans up | two env names, below |
| Live, in Discord | **`/test`** — or `/settings` ▸ **Self-test…** ▸ **Run the self-test**, the same function | the only thing no test can: what a card LOOKS like in the client | staff. ⚠️ **This said "in the test channel" until 2026-09-19** — there is no test channel since the `TEST_MODE` lift (2026-09-18 16:08). The cards go to `selftest_channel_id`, which points at `#blackbloc-logs` because that is what the KEY says, not because a guard forces it; re-point the key and they go elsewhere. **Since 2026-09-20 `/test` is the door to use**: `/test` alone behaves exactly as the button does, `/test where:#somewhere` posts this run's cards there instead without changing the key, and `/test keep:10` leaves them up for ten minutes instead of `selftest_purge_minutes`. ⚠️ **The boot run no longer happens on a live server** — `selftest_on_boot` now defaults to whatever `TEST_MODE` is, so with test mode off a deploy proves itself only if staff ask, or if the key is stored `true` by hand |

⚠️ **No API can click a Discord button.** Discord originates interactions; the bot can only answer
them. Button, select and modal handlers are proven by the pytest fakes. The self-test proves
everything up to and including the card being posted with its live view.

## The hermetic suite

```powershell
.\.venv\Scripts\python.exe -m pytest -q -n 16     # the gate's count since 2026-09-22; -n auto works too
.\.venv\Scripts\python.exe -m ruff check .
```

`-m 'not live'` is in `pyproject.toml`'s `addopts`, so `tests/live/` is **deselected** from every
default run — it never reaches the network by accident.

### A red or hung run — the junit file and the 120 s timeout (2026-09-22)

- **The gate's run writes `%TEMP%\black-bloc-gate\gate-junit.xml`** (`scripts/deploy.ps1`; any run can do the same
  with `--junitxml=<path>`). Every failed test is a `<testcase>` with a `<failure>` child, every error or crashed
  worker one with an `<error>` child; the nodeid is `classname` with dots turned into folders up to the `.py` file,
  then `::name`. The gate prints exactly that as `FAILED TESTS:`. By hand:

  ```powershell
  ([xml](Get-Content "$env:TEMP\black-bloc-gate\gate-junit.xml" -Raw)).SelectNodes("//testcase[failure or error]") |
    ForEach-Object { "$($_.classname)::$($_.name)  $($_.failure.message)$($_.error.message)" }
  ```

  No file = pytest itself was killed (KI-37), not a red suite.
- **Every test has 120 s** (`timeout = 120`, `timeout_method = "thread"` in `pyproject.toml`, `pytest-timeout` in the
  dev extras). A test that hangs past it kills its worker: the run goes on and reports
  `worker 'gwN' crashed while running '<nodeid>'` (serially the run itself ends, with a `+++ Timeout +++` stack dump).
  That line after 120+ s is a HANG with its name — read KI-26 for what the known shapes look like. A test that
  genuinely needs longer takes `@pytest.mark.timeout(<s>)`.
- **`tests/loopback.py`** is loaded into every run by `-p tests.loopback` in `addopts`. On Windows it makes every
  `socket.socketpair` (the self-pipe of every asyncio loop) close with a reset, so a run leaves no loopback
  `TIME_WAIT`. Without it a full run leaves thousands, and with a few suites on the machine the 16,384-port dynamic
  range runs dry and every worker blocks in `accept()` — the KI-26 stall. Do not remove it from `addopts`.
- **The api tests keep guide pictures in their own tmp folder** (`web_settings_at` in `tests/api/conftest.py`). A
  test bot built from `web_settings_now()` alone points at the DEFAULT database folder, which every xdist worker
  shares — that was KI-32.

⚠️ **Tests mirror the package** (`black_bloc/x.py` → `tests/test_x.py`). `tests/live/` is the one
deliberate exception and says so in its own `__init__.py`.

## The mock

```powershell
node site/mock/server.mjs        # leave it running
node site/mock/check.mjs         # in another shell
```

Both halves read `site/mock/contract.json`, so the mock and the real routers cannot drift.
`tests/api/test_contract.py` runs the same table against the real routers.

## The live api

Two env names, both required, or the whole suite skips:

| Name | What it is | Where it comes from |
|---|---|---|
| `BLACK_BLOC_LIVE_URL` | the deployed origin, e.g. the dashboard's own address | `docs/access/site.md` |
| `BLACK_BLOC_LIVE_TOKEN` | the **`OPERATOR_READ_TOKEN`** value | the owner mints it — `scripts/mint-operator-token.ps1`, [`operator-read.md`](operator-read.md) |
| `BLACK_BLOC_LIVE_SESSION` | *optional* — a staff session cookie (`__Host-bb_session`) | the browser's dev tools, on a signed-in dashboard tab |

⚠️ **The operator token is READ-ONLY by design** (`black_bloc/api/auth.py:operator_session` refuses
every method but `GET`/`HEAD` in words). So it reads the runs but **cannot start one**. The
start → poll → purge test needs `BLACK_BLOC_LIVE_SESSION`; without it that one test skips and the
rest still run.

⚠️ **A test that means to check the OPERATOR gate on a write must send the dashboard's own headers**
— `conftest.same_site_headers()` (`origin` from `BLACK_BLOC_LIVE_URL`, plus `sec-fetch-site:
same-origin`). Without them `server.py`'s `same_site_writes` middleware runs first and answers
`403 cross_site`, so the operator gate is never reached and the test proves nothing. That is
exactly what the first live run found, 2026-09-06.

```powershell
$env:BLACK_BLOC_LIVE_URL  = "https://<the dashboard host>"
$env:BLACK_BLOC_LIVE_TOKEN = "<the operator token>"     # never paste this into a doc or a log
.\.venv\Scripts\python.exe -m pytest -m live tests/live -q
```

| File | Asks |
|---|---|
| `tests/live/test_reads.py` | every GET the pages make answers 200 with the keys they read; the gateway is connected; no loop has stopped |
| `tests/live/test_selftest.py` | the operator token reads but never starts; the newest run finished; a run started by hand ends with zero failures and its cards are purged |
| `tests/live/test_refusals.py` | no token, a wrong token, a write on the read-only token and an unknown route are all refused **in words**, never a bare status |

## Gotchas that cost real time

- ⚠️ **A `TestClient` used without `with` gets a NEW event loop per request**, so anything a route
  started in the background is killed on the way out. `tests/api/test_selftest_api.py` overrides the
  shared `client` fixture with a context-managed one for exactly that reason.
- ⚠️ **`site/mock/` is NOT in the Docker image** (`Dockerfile` copies `black_bloc` and
  `site/public` only), so nothing at runtime may read `contract.json`. The self-test's `read.*`
  family walks the running FastAPI app's own route table instead.
- FastAPI keeps an included router as ONE entry in `app.routes`, not as its routes flattened —
  `selftest.walk_routes` recurses for that reason.
- A live run posts real messages into `selftest_channel_id` and deletes them again after
  `selftest_purge_minutes` — **1 minute by default** (measured 2026-09-11:
  `settings_store.SELFTEST_PURGE_MINUTES_DEFAULT` is `1`; it was **5** until 2026-09-10). If a run
  dies mid-way, the next boot's first purge tick clears the leftovers before it posts anything new.
