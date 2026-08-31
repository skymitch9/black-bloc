# Disaster recovery — rebuild Black Bloc from nothing

> **Audience:** whoever has to rebuild this with no memory of it — a weaker
> executor must be able to follow it cold. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then), secret NAMES
> only. Last verified: **2026-08-31** — only the `docs/` gap row and the
> tracking status were re-measured today (`git ls-files docs` = 48 files,
> `.gitignore` no longer lists `docs/`). The Fly/GitHub/secret inventory below
> is still the **2026-08-26 (evening)** reading and was NOT re-checked against
> the live Fly app or the Developer Portal today.
> ⚠️ **Nothing in this file has been DRILLED.** Every restore claim below is
> inference until a dated drill line says otherwise.

## 🔴 Named gaps (fix these before there is anything worth losing)

| Gap | Consequence today | Closes when |
|---|---|---|
| ~~**`docs/` is local-only**~~ **CLOSED 2026-08-31** | Was: the whole docs tree existed on ONE machine under OneDrive sync. Now `docs/` is **tracked in git and pushed** to `github.com/skymitch9/black-bloc` (owner, 2026-08-31, commit `1eb8870`) — measured: `git ls-files docs` returns 48 files. A clone restores the docs tree with the code. | Closed. ⚠️ Consequence: the repo is the backup, so **never write a secret VALUE under `docs/`** — names and custody only. |
| **No DB backup** | ⚠️ **No longer "the DB holds nothing"** — schema is at **16** and the live volume carries real rows (birthdays imported, settings, action log, polls, requests). A lost volume loses all of it. | Was "the first table with real data" — that threshold has PASSED. Add a scheduled `fly ssh sftp get` of `/data/black_bloc.sqlite3` or a dump job. **This is now an open gap, not a deferred one.** |

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
