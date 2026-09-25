# The Linux CI hang — a dead aiosqlite thread under the module database

> ✅ **2026-09-25 16:15 — merged (`fe81a137`) and shipped inside v165's image** (tests only). **CI GREEN** on GitHub Actions: run `36198821056` at `fc267114` (15:54), and the next two pushes (`gh run list`, 16:1x) — GitHub Actions has now run the fix on `main` (the *has not run this branch* note below is history). KI-26 stays `WATCHING`.

> **Audience:** Claude sessions and the owner (anyone debugging a hung or "worker crashed" test run).
> **Status:** TRACKED. **Last verified: 2026-09-25** (branch `ci-linux-hang`, off `main` `bababb65`) —
> reproduced, diagnosed and fixed in a `python:3.12-slim` container and on Windows; every number below
> was measured that day. ⚠️ **NOT verified:** GitHub Actions itself has not run this branch (the
> conductor pushes); the Windows KI-26 "D8 shape" is the same mechanism on the evidence of its own
> notes (one worker, async fixture setup, no aiosqlite thread alive), but no Windows hang was
> reproduced and dumped this session.

## Symptom

- CI (`ubuntu-latest`, `python -m pytest -q -n auto`), run 36190704964: 8166 passed, then two tests reported as
  xdist **worker crashes** (`node down: Not properly terminated`) — `test_spotlight.py::test_a_cog_load_with_no_guilds_yet_leaves_the_boot_to_on_ready`
  and `test_modmail.py::test_two_reconciles_at_boot_post_exactly_one_ticket_button`. The thread timeout
  method ends a worker with `os._exit` after 120 s, which xdist reports as a crash.
- Locally on Linux: one worker idle in `select`, its main thread inside pytest-asyncio's fixture wrapper for
  the root `db` fixture, for ever. The two named tests are the **victims**, not the cause.

## Cause (measured)

1. `tests/conftest.py` shares ONE `aiosqlite` connection per test module (`module_db`, for speed —
   `code-notes.md` ▸ *one database per module*). Each test runs on its **own** event loop.
2. aiosqlite runs every query on one worker thread; when a query finishes the thread calls
   `future.get_loop().call_soon_threadsafe(...)` on the loop that asked.
3. A test that calls `cog.cog_load()` starts the cog's `tasks.loop` (modmail's `_reconcile_loop`, and
   13 other test files call `cog_load()` too) and never stops it. The loop's first pass runs while the
   test's fixtures are torn down and queues a query on the shared connection.
4. The test's loop closes (pytest-asyncio cancels leftovers and closes it) while that query is still on
   the worker thread. When it finishes, `call_soon_threadsafe` raises `RuntimeError: Event loop is closed`;
   aiosqlite's `except BaseException` handler calls `call_soon_threadsafe` AGAIN for the exception, which
   raises the same error **out of the thread**. The worker thread is dead.
5. `Database.is_connected` still reads true (`_conn` is set), so the next test's `db` fixture queues its
   rewind query onto a queue nobody reads, and awaits it for ever. With `--timeout-method=signal` the
   timeout fires once, and then `module_db`'s own `close()` hangs the same way — the 15-minute hang the
   conductor saw.

It is a race (does the query finish before or after the loop closes?), which is why it is intermittent,
order-dependent, and far more frequent on Linux than on Windows.

### The proof

`py-spy dump` of the hung worker (container with `SYS_PTRACE`), trimmed — only TWO threads, the main one
and execnet's receiver; **no aiosqlite thread**, while the sqlite file was still open (`/proc/<pid>/fd`):

```
Thread 73 (idle): "MainThread"
    select (selectors.py:468)
    run_until_complete (asyncio/base_events.py:678)
    run (asyncio/runners.py:118)
    _async_fixture_wrapper (pytest_asyncio/plugin.py:455)
        kwargs: {"module_db": <Database ...>, "module_db_blank": {...}}    <- the root `db` fixture
    ...
Thread 75 (idle)
    read (execnet/gateway_base.py:534)
```

A scratch plugin (not committed) wrapped aiosqlite's worker thread and `Connection._execute` to record who
queued each query. On the next hang it wrote:

```
DIED during test=None
item fn=partial(sqlite3.Connection.execute, 'SELECT * FROM modmail_tickets WHERE guild_id = ? AND status = ? ...') fut=<Future cancelled>
ENQUEUED BY: test=tests/cogs/moderation/test_modmail.py::test_the_cog_registers_every_door_a_restart_has_to_dispatch (teardown)
  pytest_asyncio/plugin.py:424 finalizer -> discord/ext/tasks/__init__.py:247 _loop
  -> modmail.py:2798 _reconcile_loop -> :2819 reconcile_tickets -> loops.py:49 run -> :2828 _sweep -> :587 open_tickets
RuntimeError: Event loop is closed   (core.py:66, set_result)
  During handling ... RuntimeError: Event loop is closed   (core.py:75, set_exception)  <- the thread dies here
```

## Fix

`tests/conftest.py` — the `db` fixture now **yields**, and its teardown calls `settle(module_db)`:

- cancel every task still pending on the test's loop other than the current one, and await them all
  (pytest-asyncio would cancel them a moment later anyway; doing it here lets them finish while the
  loop is OPEN);
- then run one `SELECT 1` through the shared connection. aiosqlite's queue is FIFO on one thread, so when
  that answers, every query queued before it has already delivered its result to a loop that was still
  open. Nothing can reach a closed loop any more.

Two guards make any recurrence loud instead of silent:

- `db` setup checks the connection's worker thread and **fails at once** with
  `the module database's aiosqlite thread died: docs/info/ci-linux-hang.md` instead of hanging 120 s;
- `module_db` teardown skips `close()` when the thread is dead (it would otherwise hang the module's end).

And CI is diagnostic rather than mute: `.github/workflows/ci.yml` runs
`python -m pytest -q -n auto -rfE --timeout-method=signal`. On Linux the signal method raises inside the
hung test (a named failure with a traceback) instead of `os._exit`-ing the worker. `pyproject.toml` keeps
`timeout_method = "thread"` because Windows has no `SIGALRM`.

Why this is the root cause and not a mask: the hang needs a query in flight on the shared connection when a
test's loop closes. `settle` removes exactly that state. No timeout, retry or skip was added.

## Measured

| Run | Before the fix | After the fix |
|---|---|---|
| The pair (`test_spotlight.py` + `test_modmail.py`), `-n 2`, Linux | hung in 3 of 5 runs (loops hung at runs 2, 2 and 1) | **20 of 20 green** (360 passed each, ~9.5 s) |
| Forced dead thread (throwaway test, not committed) | — | next test **fails in 0.40 s** with the message above; module teardown does not hang |
| The pair again, `-n 2 -rfE --timeout-method=signal`, fresh copy, no scratch plugin | — | **5 of 5 green** (360 passed, 7–13 s) |
| Full suite `-n 4 -rfE --timeout-method=signal`, Linux | CI run 36190704964: 2 worker crashes; the conductor's container run: `E`s at 71 %, 92 %, 96 % | run 1: 8259 passed, **2 failed** — `tests/scripts/test_sync_personality_pool.py`, `FileNotFoundError: 'git'` (the slim image has no git; with git installed that file is 7 of 7 green); runs 2 and 3: **8261 passed, 1 skipped**, 258 s / 375 s, no hang |
| Windows gate `-n 8`, forward / `BB_REVERSE=1` | — | **8259 passed, 3 skipped** both orders (116 s / 122 s) |

## Still open (not fixed here, not observed hanging)

- `tests/api/conftest.py` `module_web` shares one connection per module the same way, and a `TestClient`
  used without `with` runs each request on a fresh loop. A route that leaves a query in flight when its
  request loop closes would kill that thread the same way. No sighting; `settle` cannot reach those loops.
- The 14 test files that call `cog_load()` still leave the cog's `tasks.loop` running until `settle`
  cancels it. That is now harmless, but a cog fixture that calls `cog_unload()` would be tidier.
