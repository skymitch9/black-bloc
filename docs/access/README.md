# access/ — how to OPERATE Black Bloc

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner, 2026-08-31 — permanently, not
> temporarily) — secret NAMES only. Last verified: **2026-09-11 08:34** — the index was checked BOTH
> ways: every row below points at a file that exists, and `ls docs/access/*.md` returns exactly
> **11** files — this index plus the **10** rows — so nothing in the folder is unlisted. Each row's
> one-line hook was re-read against its file and is still true. ⚠️ **NOT checked here:** the facts
> INSIDE each file (those were re-verified file by file in the same pass — see each one's own
> "Last verified"), and nothing in this pass met live Discord, the live Fly app or a browser.
> Before that: **2026-09-03** — one row ADDED, [`operator-read.md`](operator-read.md), by the
> operator-read-token build. Before that, **2026-08-31** — every row pointed at a file that existed.

| File | Answers |
|---|---|
| [`OWNER_GUIDE.md`](OWNER_GUIDE.md) | **Start here, owner:** before the trip (encrypt `.env`, leave the session open), the laptop once, what to look at on the road, if something looks wrong, when you're back |
| [`setup.md`](setup.md) | Local run: venv, `.env`, Developer Portal, invite, first start |
| [`deploy.md`](deploy.md) | Hosting on Fly.io: first launch, secrets, volume, redeploy, logs. The redeploy path is heavily exercised — **107** lines in [`../deploys.log`](../deploys.log), the last being **v108** on 2026-09-11 |
| [`RECOVERY.md`](RECOVERY.md) | Rebuild from nothing: inventory, secret custody, named gaps |
| [`runbook.md`](runbook.md) | **Day to day:** where everything is, the flyctl path, deploy/restart/rollback/logs, secret names, common failures and what they mean, local run, docs bookkeeping |
| [`sweeps.md`](sweeps.md) | **What the owner has not yet exercised by hand**, in priority order, with what to expect — the verification checklist. Rows **1–350** as of 2026-09-11 |
| [`operator-read.md`](operator-read.md) | **`OPERATOR_READ_TOKEN`**: the one command the OWNER runs to mint it (it never prints the value), how a session reads live state with `scripts/read.ps1`, the table of readable paths, and how to rotate or revoke. Unset = the door does not exist |
| [`personality-pool.md`](personality-pool.md) | **The shared mood manifest**: the order of operations for a roster change across both estate bots, `scripts/sync_personality_pool.py`, the two `personality_pool_*` settings, what the boot sync writes (and the one column it never touches), and how to read the `pool.in_step_with_gabi` self-test row. Added 2026-09-05; **both halves have landed since** (KI-23 closed 2026-09-05 19:45) |
| [`site.md`](site.md) | The config website: the one-hostname deploy, the custom domain, the EXACT Discord OAuth redirect URI to register, the **17** pages and the mock. It is LIVE at https://blackbloc.heygabi.ai |
| [`testing.md`](testing.md) | **How to run the tests:** the hermetic suite, the mock's contract check, and `tests/live/` against the DEPLOYED api (the two env NAMES it needs, and why the operator token cannot start a self-test). Added 2026-09-05 by the self-test build |
