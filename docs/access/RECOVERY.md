# Disaster recovery — rebuild Black Bloc from nothing

> **Audience:** whoever has to rebuild this with no memory of it — a weaker
> executor must be able to follow it cold. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then), secret NAMES
> only. Last verified: **2026-08-31** — only the `docs/` gap row and the
> tracking status were re-measured today (`git ls-files docs` = 48 files,
> `.gitignore` no longer lists `docs/`). The Fly/GitHub/secret inventory below
> is still the **2026-08-26 (evening)** reading and was NOT re-checked against
> the live Fly app or the Developer Portal today.
> ⚠️ **Drilled so far: the DB backup pull (2026-08-31, below).** Every other
> restore claim is inference until a dated drill line says otherwise.

## 🔴 Named gaps (fix these before there is anything worth losing)

| Gap | Consequence today | Closes when |
|---|---|---|
| ~~**`docs/` is local-only**~~ **CLOSED 2026-08-31** | Was: the whole docs tree existed on ONE machine under OneDrive sync. Now `docs/` is **tracked in git and pushed** to `github.com/skymitch9/black-bloc` (owner, 2026-08-31, commit `1eb8870`) — measured: `git ls-files docs` returns 48 files. A clone restores the docs tree with the code. | Closed. ⚠️ Consequence: the repo is the backup, so **never write a secret VALUE under `docs/`** — names and custody only. |
| ~~DB backup is manual~~ **CLOSED 2026-09-01** | Windows scheduled task **"BlackBloc DB backup"** (daily 04:00, StartWhenAvailable, on the owner's main machine) runs `scripts/backup_db.ps1`: consistent snapshot via `python3 -m black_bloc.dbsnapshot` on the Fly machine, sftp pull to `%USERPROFILE%\black-bloc-backups\backup-<date>.sqlite3`, keeps 14, logs to `backup.log` there. **End-to-end tested 2026-09-01** (311,296 bytes pulled, "ok" logged). | Residual: runs only while THAT machine exists and is signed into flyctl — it is machine state; re-register with the one `Register-ScheduledTask` block in `deploy.md`-style docs (or re-run the drill by hand) after a rebuild. Check `backup.log` if in doubt — a silent stop is the failure mode. |

### DB backup — the drilled procedure (2026-08-31)

```
<flyctl> ssh console --app black-bloc -C "python3 -c \"import sqlite3; s=sqlite3.connect('/data/black_bloc.sqlite3'); d=sqlite3.connect('/data/backup-drill.sqlite3'); s.backup(d); d.close(); s.close(); print('backup written')\""
<flyctl> ssh sftp get /data/backup-drill.sqlite3 %USERPROFILE%\black-bloc-backups\backup-<date>.sqlite3 --app black-bloc
<flyctl> ssh console --app black-bloc -C "rm /data/backup-drill.sqlite3"
```

Notes from the drill: use `sqlite3.backup()` on the machine first — a raw copy of the
live file can tear (WAL is in play); the image has no `sqlite3` CLI but python3 is
there. From Git Bash prefix `MSYS_NO_PATHCONV=1` or `/data/...` gets rewritten to a
Windows path. `flyctl ssh console -C` may exit with "The handle is invalid" on Windows
AFTER the command ran — trust the printed output, not the exit code. Verify a pulled
backup by opening it and counting rows (birthdays 38 as of 2026-08-31). Backups live
in `%USERPROFILE%\black-bloc-backups\` — NEVER inside the repo (the DB holds member
data and `docs/` is tracked).

## Inventory

| Asset | Where it lives | How to restore |
|---|---|---|
| Code | git — private remote `github.com/skymitch9/black-bloc` (pushed 2026-08-26) | `git clone`, then `access/setup.md` §1 |
| SQLite DB | Local: `data/black_bloc.sqlite3` (gitignored). Hosted: Fly volume `black_bloc_data` at `/data` | Copy the file back into place; schema is created on start if absent (`storage/db.py`) |
| Generated data | none yet | — |
| Machine state | none — no scheduled tasks, no installed services. The venv is disposable | `python -m venv .venv && pip install -e ".[dev]"` |
| Hosting | Fly.io app `black-bloc`, org *Sky* (`personal`), machine `85e744c4d959d8`, region `lax`, volume `black_bloc_data` (`vol_r6826q32xq583qd4`) | `deploy.md` first-launch steps recreate all of it from `fly.toml` + `Dockerfile` |

## Secrets — by NAME, with custody

> 🔐 **THE VAULT IS THE MASTER — 2026-09-02.** All nine secret values live as
> individual bare-titled items in the 1Password vault **`Black Bloc`**
> (id `2cbj6khhcydxeohuygvv7zrsju`, tags `estate`/`black-bloc`/`credential`),
> created from `.env` via the `op` CLI with owner approval; the vault is
> deliberately SEPARATE from the estate's `Estate` vault so it can be shared
> with a future Black Bloc dev without exposing estate master credentials.
> Custody order on any disagreement: **vault → `.env` (working copy) →
> `.env.enc` (offline fallback; passphrase in the owner's head)** — resolve
> toward the vault, never away from it. Rotation: change the vault item, paste
> into `.env`, then push to Fly. Laptop: open 1Password, copy each value into a
> `.env` built from the tracked `.env.example`. ⚠️ Gotcha, measured 2026-09-02:
> the `op` CLI cannot reach the desktop app from a SANDBOXED session shell
> ("cannot connect to 1Password app" / "authorization timeout" while the app
> runs fine) — it needs an unsandboxed shell plus the owner clicking the
> authorization prompts; GABI's 2026-08-26 adoption hit none of this only
> because its shells were unsandboxed.

| Name | Custody (where a copy lives / who re-mints) | Deployed copy |
|---|---|---|
| `DISCORD_TOKEN` | Discord Developer Portal → application *Black Bloc* (id `1542317881822281739`) → Bot → **Reset Token** (re-mint; old one dies). Owner's Discord login is the root of trust. | `fly secrets` on app `black-bloc` (write-only; cannot be read back) + local `.env` |
| Fly account | `flyctl auth login` as the owner's Fly login | — |
| GitHub | `gh auth` as `skymitch9` | — |
| `DEV_GUILD_ID` | Not secret; readable in Discord with Developer Mode | `fly secrets` or `[env]` |
| `SESSION_SECRET` | Re-mintable at will (any long random string) — rotating signs everyone out, nothing else | `fly secrets` + local `.env` |
| `POLL_VOTE_SECRET` | ⚠️ **NOT freely re-mintable** (set 2026-08-31): anonymous polls created while it is set key their vote hashes to it — without it those polls refuse votes in words. Custody = local `.env` + `fly secrets` (write-only). If both copies die, close the affected polls and mint a new one. | `fly secrets` + local `.env` |
| `ANTHROPIC_API_KEY` | Re-mintable at console.anthropic.com (owner's Anthropic account; rotating just swaps the key). Powers the chat "important" tier (Phase 14). ⚠️ The image must contain the `anthropic` dependency (any deploy ≥ Phase 14) or the tier silently never exists. | `fly secrets` + local `.env` (unset until the owner mints it) |
| `GROQ_API_KEY` | Re-mintable at console.groq.com (owner's Groq account, free tier). Powers the chat "simple" tier (Phase 14). | `fly secrets` + local `.env` (unset until the owner mints it) |

Every secret has a reachable copy or a recovery path: the token can always be
re-minted from the portal (invalidating any leaked copy in the same motion);
`POLL_VOTE_SECRET` is the one whose loss has a real cost — see its row.

## Full rebuild, in order

1. `git clone` (or copy the folder) → `access/setup.md` §1.
2. Re-mint `DISCORD_TOKEN` in the portal (§2 there) if the old one is lost.
3. Restore the DB file if one exists; otherwise start clean — the bot creates
   the schema.
4. Local: `python -m black_bloc`. Hosted: `deploy.md` from "First launch".

## Drill log

*(none yet — add `YYYY-MM-DD — what was drilled — result`)*
