# access/ — how to OPERATE Black Bloc

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner, 2026-08-31 — permanently, not
> temporarily) — secret NAMES only. Last verified: **2026-08-31** — every row below points at a file that
> exists (checked today); the files' own contents carry their own "Last verified" dates.

| File | Answers |
|---|---|
| [`OWNER_GUIDE.md`](OWNER_GUIDE.md) | **Start here, owner:** before the trip (encrypt `.env`, leave the session open), the laptop once, what to look at on the road, if something looks wrong, when you're back |
| [`setup.md`](setup.md) | Local run: venv, `.env`, Developer Portal, invite, first start |
| [`deploy.md`](deploy.md) | Hosting on Fly.io: first launch, secrets, volume, redeploy, logs. Verified daily since 2026-08-26 (see `../deploys.log`) |
| [`RECOVERY.md`](RECOVERY.md) | Rebuild from nothing: inventory, secret custody, named gaps |
| [`runbook.md`](runbook.md) | **Day to day:** where everything is, the flyctl path, deploy/restart/rollback/logs, secret names, common failures and what they mean, local run, docs bookkeeping |
| [`sweeps.md`](sweeps.md) | **What the owner has not yet exercised by hand**, in priority order, with what to expect — the verification checklist |
| [`site.md`](site.md) | The config website: Pages deploy, the custom domain, and the EXACT Discord OAuth redirect URI to register. Verified live 2026-08-26/27 (single hostname on the Fly app) |
