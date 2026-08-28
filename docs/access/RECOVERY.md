# Disaster recovery — rebuild Black Bloc from nothing

> **Audience:** whoever has to rebuild this with no memory of it — a weaker
> executor must be able to follow it cold. **Status:** LOCAL ONLY (gitignored 2026-08-26), secret NAMES
> only. Last verified: **2026-08-26 (evening)** — inventory checked against
> the repo, GitHub and the Fly app after the first deploy.
> ⚠️ **Nothing in this file has been DRILLED.** Every restore claim below is
> inference until a dated drill line says otherwise.

## 🔴 Named gaps (fix these before there is anything worth losing)

| Gap | Consequence today | Closes when |
|---|---|---|
| **`docs/` is local-only** | The whole docs tree (TODO/DONE/runbooks/this file) exists on ONE machine, under OneDrive sync. OneDrive is sync, not backup — a bad edit syncs too. | A periodic archive of `docs/` to somewhere else (the estate's R2 docs backup, `catalog-platform/scripts/backup-docs.mjs`, is the precedent) |
| **No DB backup** | Acceptable now: the DB holds nothing. | The first table with real data → add a scheduled `fly ssh sftp get` or a dump job |

## Inventory

| Asset | Where it lives | How to restore |
|---|---|---|
| Code | git — private remote `github.com/skymitch9/black-bloc` (pushed 2026-08-26) | `git clone`, then `access/setup.md` §1 |
| SQLite DB | Local: `data/black_bloc.sqlite3` (gitignored). Hosted: Fly volume `black_bloc_data` at `/data` | Copy the file back into place; schema is created on start if absent (`storage/db.py`) |
| Generated data | none yet | — |
| Machine state | none — no scheduled tasks, no installed services. The venv is disposable | `python -m venv .venv && pip install -e ".[dev]"` |
| Hosting | Fly.io app `black-bloc`, org *Sky* (`personal`), machine `85e744c4d959d8`, region `lax`, volume `black_bloc_data` (`vol_r6826q32xq583qd4`) | `deploy.md` first-launch steps recreate all of it from `fly.toml` + `Dockerfile` |

## Secrets — by NAME, with custody

| Name | Custody (where a copy lives / who re-mints) | Deployed copy |
|---|---|---|
| `DISCORD_TOKEN` | Discord Developer Portal → application *Black Bloc* (id `1542317881822281739`) → Bot → **Reset Token** (re-mint; old one dies). Owner's Discord login is the root of trust. | `fly secrets` on app `black-bloc` (write-only; cannot be read back) + local `.env` |
| Fly account | `flyctl auth login` as the owner's Fly login | — |
| GitHub | `gh auth` as `skymitch9` | — |
| `DEV_GUILD_ID` | Not secret; readable in Discord with Developer Mode | `fly secrets` or `[env]` |

There is no secret with NO reachable copy: the token can always be re-minted
from the portal, which is the intended recovery path (invalidating any leaked
copy in the same motion).

## Full rebuild, in order

1. `git clone` (or copy the folder) → `access/setup.md` §1.
2. Re-mint `DISCORD_TOKEN` in the portal (§2 there) if the old one is lost.
3. Restore the DB file if one exists; otherwise start clean — the bot creates
   the schema.
4. Local: `python -m black_bloc`. Hosted: `deploy.md` from "First launch".

## Drill log

*(none yet — add `YYYY-MM-DD — what was drilled — result`)*
