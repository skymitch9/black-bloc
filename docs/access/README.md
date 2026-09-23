# access/ — how to OPERATE Black Bloc

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner, 2026-08-31 — permanently, not
> temporarily) — secret NAMES only. Last verified: **2026-09-23 15:1x — the `deploy.md` and `testing.md` ROWS only**, at the
> v160 + v161 ritual: [`../deploys.log`](../deploys.log) is **160** lines (`grep -c .`), the last being **v161** `c8d2403d`; the `testing.md` row names its new stale-mock gotcha. `ls docs/access/*.md` still **12**. ⚠️ **NOT checked:** every other row's number or the facts inside any file.
> Before that, **2026-09-23 14:1x — the `deploy.md` and `site.md` ROWS only**, at the
> v158 + v159 ritual: [`../deploys.log`](../deploys.log) is **158** lines (`grep -c .`), the last being **v159** `c54f14a8`;
> `ls site/public/*.html` is **22** (`channels.html`). `ls docs/access/*.md` still **12**. ⚠️ **NOT checked:** every other
> row's number or the facts inside any file.
> Before that, **2026-09-23 04:3x — the `deploy.md` and `testing.md` ROWS only**, at the v157
> ritual: [`../deploys.log`](../deploys.log) is **156** lines (`grep -c .`), the last being **v157** `e9ecd0d0`; the `testing.md`
> row now names the sections the code-health round added (the environment fixture, the junit file, the 120 s timeout, the loopback
> plugin). `ls docs/access/*.md` still **12**. ⚠️ **NOT checked:** every other row's number or the facts inside any file.
> Before that, **2026-09-22 21:2x — the `deploy.md` ROW only**, at the v156
> ritual: [`../deploys.log`](../deploys.log) is **155** lines (`grep -c .`), the last being **v156** `4fb69e00`;
> `ls docs/access/*.md` still **12**. ⚠️ **NOT checked:** every other row's number or the facts inside any file.
> Before that, **2026-09-22 — the `deploy.md` ROW only**, at the v155
> ritual: [`../deploys.log`](../deploys.log) is **154** lines (`grep -c .`), the last being **v155**
> `a285afc7` at 2026-09-22 13:35; the row had said *150 / v151*. Counted while here: `ls
> docs/access/*.md` still returns **12** files (this index plus **11** rows), unchanged. ⚠️ **NOT checked
> at that pass:** every other row's number, the facts inside any file, and nothing in it met live Discord
> or a browser. Before that, **2026-09-19** — the index was re-checked BOTH ways by
> script: `ls docs/access/*.md` returns **12** files (this index plus **11** rows), every row points at a
> file that exists, and every file has exactly one row — **no duplicates, nothing unlisted**. Two rows
> carried a stale NUMBER and are fixed: `deploy.md` said *107 lines, last v108* (**140** lines, last
> **v141** — counted off [`../deploys.log`](../deploys.log)) and `sweeps.md` said *rows 1–350*
> (**1–620**). ⚠️ **NOT checked here:** the facts INSIDE each file — this pass re-verified
> `setup.md`, `testing.md`, `RECOVERY.md`, `runbook.md`, `OWNER_GUIDE.md` and `site.md` individually
> (see each one's own *Last verified*) and did **not** re-read `deploy.md`, `operator-read.md`,
> `personality-pool.md` or `guides-capture.md` beyond their headers. Nothing in this pass met live
> Discord, the Fly console or a browser. Before that, **2026-09-11 08:34** — the index was checked BOTH
> ways: every row below points at a file that exists, and `ls docs/access/*.md` returns exactly
> **12** files — this index plus the **11** rows (2026-09-16: `guides-capture.md` added by the Guides G2 build) — so nothing in the folder is unlisted. Each row's
> one-line hook was re-read against its file and is still true. ⚠️ **NOT checked here:** the facts
> INSIDE each file (those were re-verified file by file in the same pass — see each one's own
> "Last verified"), and nothing in this pass met live Discord, the live Fly app or a browser.
> Before that: **2026-09-03** — one row ADDED, [`operator-read.md`](operator-read.md), by the
> operator-read-token build. Before that, **2026-08-31** — every row pointed at a file that existed.

| File | Answers |
|---|---|
| [`OWNER_GUIDE.md`](OWNER_GUIDE.md) | **Start here, owner:** before the trip (encrypt `.env`, leave the session open), the laptop once, what to look at on the road, if something looks wrong, when you're back |
| [`setup.md`](setup.md) | Local run: venv, `.env`, Developer Portal, invite, first start |
| [`deploy.md`](deploy.md) | Hosting on Fly.io: first launch, secrets, volume, redeploy, logs. The redeploy path is heavily exercised — **160** lines in [`../deploys.log`](../deploys.log), the last being **v161** on 2026-09-23 15:03 (counted 2026-09-23 15:1x at the v161 ritual; it said 158 / v159). Its *gate's pytest step* section is the `-n 16` / `-rfE` / junit / 120 s timeout gate, first run for real by v157 |
| [`RECOVERY.md`](RECOVERY.md) | Rebuild from nothing: inventory, secret custody, named gaps |
| [`runbook.md`](runbook.md) | **Day to day:** where everything is, the flyctl path, deploy/restart/rollback/logs, secret names, common failures and what they mean, local run, docs bookkeeping |
| [`sweeps.md`](sweeps.md) | **What the owner has not yet exercised by hand**, in priority order, with what to expect — the verification checklist. Rows **1–620** as of 2026-09-18 (counted 2026-09-19; it said 1–350) |
| [`operator-read.md`](operator-read.md) | **`OPERATOR_READ_TOKEN`**: the one command the OWNER runs to mint it (it never prints the value), how a session reads live state with `scripts/read.ps1`, the table of readable paths, and how to rotate or revoke. Unset = the door does not exist |
| [`personality-pool.md`](personality-pool.md) | **The shared mood manifest**: the order of operations for a roster change across both estate bots, `scripts/sync_personality_pool.py`, the two `personality_pool_*` settings, what the boot sync writes (and the one column it never touches), and how to read the `pool.in_step_with_gabi` self-test row. Added 2026-09-05; **both halves have landed since** (KI-23 closed 2026-09-05 19:45) |
| [`site.md`](site.md) | The config website: the one-hostname deploy, the custom domain, the EXACT Discord OAuth redirect URI to register, the **22** pages (re-counted 2026-09-23 at the v159 ritual, `ls site/public/*.html` — `channels.html` joined with v159; it said 21) and the mock. It is LIVE at https://blackbloc.heygabi.ai |
| [`guides-capture.md`](guides-capture.md) | **After a deploy whose `release.json` names a feature:** the step-by-step a Claude session follows to re-shoot the guide screenshots that went stale — read `/api/guides/stale` with the operator token, shoot the cards the self-test already posted in the owner's own Discord tab (⚠️ **pressing nothing on his account**), `zoom` straight to disk with `save_to_disk` (no Pillow), upload through the guide page's own **Replace screenshot…**. Added 2026-09-16 by the Guides G2 build. 🔴 **Never drilled** |
| [`testing.md`](testing.md) | **How to run the tests:** the hermetic suite, the mock's contract check, and `tests/live/` against the DEPLOYED api (the two env NAMES it needs, and why the operator token cannot start a self-test). Since v157 (2026-09-23) also: the suite clears its own environment (the session fixture in `tests/conftest.py`), and *A red or hung run* — reading the gate's junit file, the 120 s per-test timeout, and the `tests/loopback.py` plugin behind KI-26. Since 2026-09-23 its *Gotchas* name the stale-mock trap (a check.mjs mismatch on fields the code plainly has = an old mock still on the port). Added 2026-09-05 by the self-test build |
