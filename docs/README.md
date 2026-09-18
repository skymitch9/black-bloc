# Black Bloc — docs map

> **Audience:** Claude sessions first, the owner second. **Status:** TRACKED
> — `docs/` is in git and pushed (owner, 2026-08-31: "actually lets keep it
> tracked", commit `1eb8870`, which also dropped `docs/` from `.gitignore`).
> This retires the 2026-08-26 local-only rule, under which the tree was
> gitignored and purged from GitHub history. ⚠️ A clone now carries this tree,
> so: **secret NAMES only, never values.** See `access/RECOVERY.md`.
> Last verified: **2026-09-11 08:32** — a docs-wide staleness pass (owner: "Update
> all docs"), re-measured off `main` at `1d090e5`, which is **v108 LIVE** (merge
> `73e2e44` of `where-smart`, deployed 2026-09-11 00:37): `pytest -n auto`
> (**5,546 passed**, 40 s), `SCHEMA_VERSION` (**34**), `len(settings_store.KEY_TYPES)`
> (**202** registry keys), `bot.py:COGS` (**19 cogs**), the command tree built the way
> `tests/test_bot.py` does (**29** top-level commands, **29** leaves, **zero**
> `app_commands.Group`s left), `site/mock/contract.json` (**17 pages / 150 routes /
> 115 action kinds**), `docs/deploys.log` (**107 lines**, last = v108),
> `git ls-files docs` (**94 files**), `ls site/public/*.html` (**17**).
> ⚠️ **NOT checked:** anything against the live bot or the live dashboard **in a
> browser**; no Discord button was pressed and `python -m black_bloc` was not booted
> (a worktree holds no token); the mock's *live* check (`node site/mock/check.mjs`
> needs `site/mock/server.mjs` running — the 17/150 figures were read out of
> `contract.json`, which is what both halves read); `info/code-notes.md`'s `path:line`
> keys; the `archive/` dumps' contents; and the per-item wording of
> `info/review-checklist.md`. Before that,
> **2026-09-02** — re-measured on the Phase 15 (F14) branch,
> which was then NOT merged and NOT deployed: `pytest` (**2714 tests**),
> `node site/mock/check.mjs` (**17 pages / 111 routes**),
> `ruff check black_bloc tests site` (clean), `SCHEMA_VERSION` (**21**),
> `bot.py:COGS` (**15 cogs**, **37** top-level slash commands). Before that,
> 2026-08-31 — a docs-wide staleness audit measured against
> the repo: `git log` / `deploys.log` (37 deploys, last `8036918` at 2026-08-27
> 20:15), `pytest --co` (**2158 tests**), `node site/mock/check.mjs` (**17
> pages / 89 routes**), `SCHEMA_VERSION` (**16**), `bot.py:COGS` (**14 cogs**).
>
> 📐 **The rules for this tree — filing, formatting, when to move things — live
> in [`DOCS_STANDARD.md`](DOCS_STANDARD.md) (§9 is the only project-specific
> part).** Read once; do not restate elsewhere.

**What this project is:** *Black Bloc*, a Discord **moderation and content**
bot. Python 3.12 + `discord.py` (gateway bot, one always-on process), SQLite
for state, and a FastAPI companion that serves both the API and the dashboard
from **one** hostname — https://blackbloc.heygabi.ai (`API_ENABLED=true` in
`fly.toml`; it was "optional, off by default" until Phase 8a). Separate from the
estate's other bot (GABI, in `catalog-platform`, which is a Cloudflare Worker
using the HTTP-interactions model — a different animal; see `info/hosting.md`
for why).

---

## The tree

| File | Question it answers | Read when |
|---|---|---|
| [`TODO.md`](TODO.md) | What is active, blocked, or waiting on the owner? | **Every session, first** |
| [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) | Is this wrong on purpose? | **Before fixing anything** |
| [`DONE.md`](DONE.md) | Was this solved before, and why that way? | When something feels familiar |
| [`access/`](access/README.md) | How do I run / deploy / reach / recover it? | Operating it |
| [`info/`](info/README.md) | How does it work, and why built this way? | Changing it |
| [`archive/`](archive/README.md) | What did this look like before? | Rarely |
| [`DOCS_STANDARD.md`](DOCS_STANDARD.md) | What shape must this tree keep? | Before adding a doc |
| [`deploys.log`](deploys.log) | What is live, and when did it ship? | Before any deploy or rollback |

⚠️ **Everything under `docs/` is reachable from this table.** The eight rows above
are the *whole* top level (nothing else may live there — `DOCS_STANDARD.md` §1).
The individual files in `access/` (**10** beside its index) and `info/` (**88**
beside its index — measured 2026-09-18, the 66 had drifted since 2026-09-11 —, plus the `mock-direction-a/` folder)
are listed by their own indexes, [`access/README.md`](access/README.md) and
[`info/README.md`](info/README.md), not here — this page does not duplicate an
index (§7). `archive/` holds the retired docs and the one-off `current-bots/`
dumps, indexed by [`archive/README.md`](archive/README.md).

## Ten-second orientation

- **Run it:** [`access/setup.md`](access/setup.md) — venv, `.env`, Developer
  Portal steps, `python -m black_bloc`.
- **Host it:** [`info/hosting.md`](info/hosting.md) has the decision and the
  trade-off; [`access/deploy.md`](access/deploy.md) has the Fly.io runbook.
- **Extend it:** [`info/architecture.md`](info/architecture.md) — where a new
  feature goes (a cog under `black_bloc/cogs/moderation/` or `content/`).
- **Traps:** [`info/gotchas.md`](info/gotchas.md) — privileged intents,
  command-sync rate limits, SQLite inside a OneDrive folder.
