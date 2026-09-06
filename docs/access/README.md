# access/ — how to OPERATE Black Bloc

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner, 2026-08-31 — permanently, not
> temporarily) — secret NAMES only. Last verified: **2026-08-31** — every row below points at a file that
> exists (checked today); the files' own contents carry their own "Last verified" dates.
> Since then: **2026-09-03** — one row ADDED, [`operator-read.md`](operator-read.md), by the
> operator-read-token build. Nothing else in this index was re-checked that day.

| File | Answers |
|---|---|
| [`OWNER_GUIDE.md`](OWNER_GUIDE.md) | **Start here, owner:** before the trip (encrypt `.env`, leave the session open), the laptop once, what to look at on the road, if something looks wrong, when you're back |
| [`setup.md`](setup.md) | Local run: venv, `.env`, Developer Portal, invite, first start |
| [`deploy.md`](deploy.md) | Hosting on Fly.io: first launch, secrets, volume, redeploy, logs. Verified daily since 2026-08-26 (see `../deploys.log`) |
| [`RECOVERY.md`](RECOVERY.md) | Rebuild from nothing: inventory, secret custody, named gaps |
| [`runbook.md`](runbook.md) | **Day to day:** where everything is, the flyctl path, deploy/restart/rollback/logs, secret names, common failures and what they mean, local run, docs bookkeeping |
| [`sweeps.md`](sweeps.md) | **What the owner has not yet exercised by hand**, in priority order, with what to expect — the verification checklist |
| [`operator-read.md`](operator-read.md) | **`OPERATOR_READ_TOKEN`**: the one command the OWNER runs to mint it (it never prints the value), how a session reads live state with `scripts/read.ps1`, the table of readable paths, and how to rotate or revoke. Unset = the door does not exist |
| [`personality-pool.md`](personality-pool.md) | **The shared mood manifest**: the order of operations for a roster change across both estate bots, `scripts/sync_personality_pool.py`, the two `personality_pool_*` settings, what the boot sync writes (and the one column it never touches), and how to read the `pool.in_step_with_gabi` self-test row. Added 2026-09-05 by the personality-pool build (Black Bloc half) |
| [`site.md`](site.md) | The config website: Pages deploy, the custom domain, and the EXACT Discord OAuth redirect URI to register. Verified live 2026-08-26/27 (single hostname on the Fly app) |
| [`testing.md`](testing.md) | **How to run the tests:** the hermetic suite, the mock's contract check, and `tests/live/` against the DEPLOYED api (the two env NAMES it needs, and why the operator token cannot start a self-test). Added 2026-09-05 by the self-test build |
