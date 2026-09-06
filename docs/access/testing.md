# Testing — the hermetic suite, the mock, and the live api

> **Audience:** Claude sessions and the owner. **Status:** TRACKED — ⚠️ secret NAMES only.
> Last verified: **2026-09-05** — the counts below were MEASURED on the wave-5 self-test branch
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

## The three layers, and what each one proves

| Layer | Command | Proves | Needs |
|---|---|---|---|
| Hermetic | `pytest -q -n auto` | every module, every route shape, every panel card, against fakes | nothing but the venv |
| Mock | `node site/mock/server.mjs` then `node site/mock/check.mjs` | the PAGES' half of the contract: the mock answers the same shapes the real routers do | node |
| Live | `pytest -m live tests/live` | the DEPLOYED host answers, the bot is connected, a self-test run really exercises Discord and cleans up | two env names, below |
| Live, in Discord | `/settings` ▸ **Self-test…** ▸ **Run the self-test** | the only thing no test can: what a card LOOKS like in the client | staff, in the test channel |

⚠️ **No API can click a Discord button.** Discord originates interactions; the bot can only answer
them. Button, select and modal handlers are proven by the pytest fakes. The self-test proves
everything up to and including the card being posted with its live view.

## The hermetic suite

```powershell
.\.venv\Scripts\python.exe -m pytest -q -n auto
.\.venv\Scripts\python.exe -m ruff check .
```

`-m 'not live'` is in `pyproject.toml`'s `addopts`, so `tests/live/` is **deselected** from every
default run — it never reaches the network by accident.

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
  `selftest_purge_minutes` (5 by default). If a run dies mid-way, the next boot's first purge tick
  clears the leftovers before it posts anything new.
