# Disaster recovery — rebuild Black Bloc from nothing

> **Audience:** whoever has to rebuild this with no memory of it — a weaker
> executor must be able to follow it cold. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then), secret NAMES
> only. Last verified: **2026-09-19** — the docs staleness pass after the **TEST_MODE lift**.
> What changed here: the `docs/` row's file count (**`git ls-files docs` = 119**, not 94) and —
> the important one — **the secret-ROTATION gap is CLOSED, not open**. On 2026-09-18 17:1x the
> owner settled it (*"i think we're good if we scrub git history"*) and the measurement backed
> him: the `.env.enc` purge and force-push happened **2026-09-10 16:55**, the visibility flip
> **20:06**, so the encrypted file was never in a PUBLIC history; the two commits that carried
> it (`66eea8b`, `8e81a03`) are dangling in the local clone only. That is recorded in
> [`../DONE.md`](../DONE.md) (*2026-09-18 — The repo is PUBLIC*), which **owns** the decision;
> this file owns the CUSTODY. ⚠️ Leaving a recovery doc saying twenty-one secrets are due
> rotation when the owner has ruled otherwise is exactly the kind of stale fact this file's own
> header warns about, so the row below now says both. ⚠️ **NOT checked today:** anything against
> the live Fly app, the Fly dashboard, the Discord Developer Portal, 1Password or a browser; no
> restore was attempted, no drill was run, and the machine and volume ids are still the
> 2026-08-26 reading. ⚠️ **`TEST_MODE` is a Fly secret and is now `false`** (2026-09-18 16:08) —
> a rebuild that restores it as `true` would silence the bot in every channel but
> `TEST_CHANNEL_ID`, which would look exactly like a broken restore. Before that,
> **2026-09-11 08:36** — re-read against the repo (`fly.toml`,
> `.env.example`, `black_bloc/config.py`, `.gitignore`, `git ls-files`). What changed:
> 🔴 **the GitHub repo is PUBLIC** (since 2026-09-10 20:06) — the Inventory said
> "private", which is the single most dangerous stale fact a recovery doc can carry
> now that `docs/` is tracked; **`git ls-files docs` is 94 files**, not 48;
> **"Machine state: none"** was wrong — the daily DB-backup scheduled task IS machine
> state, and the named-gaps row above already said so, so the two rows disagreed;
> **four secret NAMES were missing** from the custody table (`DISCORD_CLIENT_ID`,
> `DISCORD_CLIENT_SECRET`, `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`) even though
> `.env.example` lists them and the vault holds them; **`OPERATOR_READ_TOKEN` was
> minted 2026-09-06** (that was already noted below the table and is now in the
> header too); and the **Drill log was empty** while two drills were described in the
> body. Re-measured today: `fly.toml` names app `black-bloc`, region `lax`, volume
> `black_bloc_data` → `/data`, and `DATABASE_PATH=/data/black_bloc.sqlite3`;
> `.env.example` carries **21** names (**23** since 09:25: `OPERATOR_READ_TOKEN` and `SESSION_COOKIE_SAMESITE`, both read by `config.py`, were added after the docs pass found them missing — the rotation list is still the 21 secrets plus `OPERATOR_READ_TOKEN` if it was set).
> ⚠️ **NOT checked today:** anything against the live Fly app, the Fly dashboard, the
> Discord Developer Portal, 1Password or a browser — no restore was attempted, and the
> machine and volume ids below are still the 2026-08-26 reading.
> ⚠️ **Drilled so far: the DB backup pull (2026-08-31) and the end-to-end scheduled
> backup (2026-09-01) — both in the Drill log at the foot.** Every other restore claim
> is inference until a dated drill line says otherwise. Before that, **2026-09-03** —
> one row was ADDED to the secrets table, `OPERATOR_READ_TOKEN`. Before that,
> **2026-08-31** — the `docs/` gap row and the tracking status (`git ls-files docs` =
> 48 files, `.gitignore` no longer lists `docs/`).

## 🔴 Named gaps (fix these before there is anything worth losing)

| Gap | Consequence today | Closes when |
|---|---|---|
| ~~**`docs/` is local-only**~~ **CLOSED 2026-08-31** | Was: the whole docs tree existed on ONE machine under OneDrive sync. Now `docs/` is **tracked in git and pushed** to `github.com/skymitch9/black-bloc` (owner, 2026-08-31, commit `1eb8870`) — measured 2026-09-19: `git ls-files docs` returns **119** files (94 on 2026-09-11, 48 on 2026-08-31). A clone restores the docs tree with the code. | Closed. 🔴 Consequence, **sharper since the repo went PUBLIC 2026-09-10**: the docs tree is world-readable, so **never write a secret VALUE under `docs/`** — names and custody only. |
| ~~🔴 **Every secret named in `.env.example` is due a ROTATION**~~ **CLOSED 2026-09-18 — no rotation needed** | Was: `.env.enc` (an OpenSSL-encrypted copy of the whole `.env`) sat in the tree and in two commits before the repo was made public, so it had to be treated as **exposed**. **Measured since:** the purge (`git filter-repo`, force-push) ran **2026-09-10 16:55** and the repo went public **2026-09-10 20:06** — the purge came FIRST, so the file was never in a public history, and the two commits that carried it (`66eea8b`, `8e81a03`) are dangling in the local clone only. Owner, 2026-09-18 17:1x: *"i think we're good if we scrub git history"*. | Closed. ⚠️ **The custody table below is still the live document** — every name in it must have a reachable copy whether or not it was rotated, and that is a different question from exposure. Reopen this row only if a NEW leak is found; the decision itself lives in [`../DONE.md`](../DONE.md) (*2026-09-18 — The repo is PUBLIC*). |
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
| Code | git — `github.com/skymitch9/black-bloc`, 🔴 **PUBLIC since 2026-09-10 20:06** (was private; made public so GitHub Actions would run, `.env.enc` purged from history first). A clone needs no credentials — and neither does anyone else's. `docs/` is tracked, so **no secret VALUE may ever be written under it** | `git clone`, then `access/setup.md` §1 |
| SQLite DB | Local: `DATABASE_PATH` — `C:/Users/nbasl/black-bloc-data/black_bloc.sqlite3` on the owner's machine since KI-1 was closed (the `data/` default is gitignored and inert). Hosted: Fly volume `black_bloc_data` mounted at `/data`, file `/data/black_bloc.sqlite3` (`fly.toml` `[env] DATABASE_PATH`) | Copy the file back into place; the schema (**34** as of 2026-09-11) is created on start if absent and migrations are additive-only (`storage/db.py`) |
| Backups | `%USERPROFILE%\black-bloc-backups\backup-<date>.sqlite3`, 14 kept, written by the daily scheduled task below. **NEVER inside the repo** — the DB holds member data and the repo is public | Copy one into `DATABASE_PATH`, or sftp it back onto the volume |
| Guide screenshots | Fly volume `black_bloc_data`, folder **`/data/guides/`** — one file per `guide_media` row (`black_bloc/guides.py:media_root`, which is `DATABASE_PATH`'s parent plus `guides`). ⚠️ **They are NOT in the SQLite snapshot**, and a `guide_media` row whose file is gone renders as a broken picture, so the two travel together. `scripts/backup_db.ps1` tars the folder on the machine and pulls it to `%USERPROFILE%\black-bloc-backups\guides-<date>.tar`, 14 kept. Empty until the first capture session, and the backup log says `NO SHOTS` when it is | `flyctl ssh sftp shell --app black-bloc` and put the tar back at `/data`, then `cd /data && tar xf guides-backup.tar`. Nothing else is needed: the rows point at file names only. Losing them costs re-shooting, which is [`guides-capture.md`](guides-capture.md) — not data loss |
| Generated data | none — everything is either in the DB or regenerated at boot (the personality-pool sync, the birthday import, the chat intent seed) | — |
| Machine state | ⚠️ **NOT none.** The Windows scheduled task **"BlackBloc DB backup"** (daily 04:00, `scripts/backup_db.ps1`) exists only on the owner's main machine, and it needs `flyctl` installed and signed in there. Also machine-local: `flyctl auth login`, `gh auth`, the `BLACK_BLOC_OPERATOR_TOKEN` User environment variable, and the `.claude` junction to `C:\lcw\onedrive-excluded\black_bot_baf\.claude`. The venv is disposable | `python -m venv .venv && pip install -e ".[dev]"`; re-register the scheduled task; `winget install --id Fly-io.flyctl` then `flyctl auth login`; re-mint the operator token (`access/operator-read.md`) |
| Hosting | Fly.io app `black-bloc`, org *Sky* (`personal`), machine `85e744c4d959d8`, region `lax`, volume `black_bloc_data` (`vol_r6826q32xq583qd4`) | `deploy.md` first-launch steps recreate all of it from `fly.toml` + `Dockerfile` |
| Image packages (not just Python) | ⚠️ **Since branch `minutes` the image installs an OS package: `libopus0`** (`Dockerfile`, one `apt-get` layer above the `pip install`). It is what decodes what people say in a voice meeting — `discord.py` bundles the Opus DLL on Windows only and asks the system for it everywhere else, so a rebuilt image WITHOUT it boots fine and every `/minutes` Start refuses in words (*the Opus audio library is not loaded on this host*). ffmpeg is deliberately NOT installed; the receive path never shells out | Rebuild from the repo `Dockerfile` — it is the only home for that line. To check a running machine: `flyctl ssh console --app black-bloc -C "python -c 'import discord.opus as o; print(o._load_default())'"` should print `True` |

## Secrets — by NAME, with custody

> 🔐 **THE VAULT IS THE MASTER — 2026-09-02.** All nine secret values live as
> individual bare-titled items in the 1Password vault **`Black Bloc`**
> (id `2cbj6khhcydxeohuygvv7zrsju`, tags `estate`/`black-bloc`/`credential`),
> created from `.env` via the `op` CLI with owner approval; the vault is
> deliberately SEPARATE from the estate's `Estate` vault so it can be shared
> with a future Black Bloc dev without exposing estate master credentials.
> Custody order on any disagreement: **vault → `.env` (working copy) →
> `.env.enc` (offline fallback, kept OUTSIDE git since 2026-09-10 — the repo is public; passphrase in the owner's head)** — resolve
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
| `DISCORD_CLIENT_ID` | **Not secret**, but sign-in is off without it (`site_login_configured` is false) — Developer Portal → Black Bloc → OAuth2 | `fly secrets` + local `.env` |
| `DISCORD_CLIENT_SECRET` | Re-mintable in the Developer Portal → OAuth2 → **Reset Secret**. Rotating breaks sign-in until Fly has the new value | `fly secrets` + local `.env` |
| `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET` | Re-mintable at dev.twitch.tv/console/apps (owner's Twitch account). **Fallback path only** for the go-live feed — Discord presence is primary — so losing them costs a fallback, not the feature | `fly secrets` + local `.env` |
| `SESSION_SECRET` | Re-mintable at will (any long random string, ≥32 chars) — rotating signs everyone out, nothing else | `fly secrets` + local `.env` |
| `POLL_VOTE_SECRET` | ⚠️ **NOT freely re-mintable** (set 2026-08-31): anonymous polls created while it is set key their vote hashes to it — without it those polls refuse votes in words. Custody = local `.env` + `fly secrets` (write-only). If both copies die, close the affected polls and mint a new one. | `fly secrets` + local `.env` |
| `OPERATOR_READ_TOKEN` | **Freely re-mintable — nothing depends on the old value.** The OWNER mints it (never a session) with the one command in [`operator-read.md`](operator-read.md), which sets the Fly secret and the operator PC's `BLACK_BLOC_OPERATOR_TOKEN` in one motion without printing it. Custody = Fly (write-only) + the HKCU environment on the operator PC; there is deliberately no third copy. Losing both costs one re-mint. It only ever grants **read** access to `/api/*` — a leaked one is revoked with `flyctl secrets unset OPERATOR_READ_TOKEN`, which is immediate and total. | `fly secrets` (unset until the owner mints it) — **never** in `.env` on the host |
| `ANTHROPIC_API_KEY` | Re-mintable at console.anthropic.com (owner's Anthropic account; rotating just swaps the key). Powers the chat "important" tier (Phase 14). ⚠️ The image must contain the `anthropic` dependency (any deploy ≥ Phase 14) or the tier silently never exists. | `fly secrets` + local `.env` (unset until the owner mints it) |
| `GROQ_API_KEY` | Re-mintable at console.groq.com (owner's Groq account, free tier). Powers the chat "simple" tier (Phase 14). | `fly secrets` + local `.env` (unset until the owner mints it) |
| `YOUTUBE_API_KEY` | **Minted 2026-09-17** in the Google Cloud project **`black-bloc`** (its own project, separate from the other apps — owner's choice so future billing can be split), *YouTube Data API v3* enabled. Re-mint at console.cloud.google.com → APIs & Services → Credentials on that project, then `flyctl secrets set YOUTUBE_API_KEY=…` and update the vault item. Powers the live-stream search + confirm (v133: ~101 units per stream), the `@handle` lookup and the live/upload check. Losing it costs nothing a re-mint does not restore; live detection degrades to the keyless `/live` link. | 1Password vault **Black Bloc**, item *YOUTUBE_API_KEY — Black Bloc (YouTube Data API v3)* (made 2026-09-17 23:38); the Fly secret (set 2026-09-17 18:03); the gitignored `.env` |

Every secret has a reachable copy or a recovery path: the token can always be
re-minted from the portal (invalidating any leaked copy in the same motion);
`POLL_VOTE_SECRET` is the one whose loss has a real cost — see its row.
✅ **`YOUTUBE_API_KEY` has a value in three places since 2026-09-17** (the vault item, the Fly secret, `.env`) — the paragraph below is kept for the record of when it had none. It is listed so a
rebuild does not treat its absence as a missing backup: the vault still holds
**nine** items, and this is the tenth name.
**`OPERATOR_READ_TOKEN` was minted 2026-09-06** (owner, `scripts/mint-operator-token.ps1`; live
since v97) and is deliberately **not a vault item**: its custody
is Fly plus the operator PC's own environment, because a re-mint costs nothing
and nothing depends on the old value. A rebuild simply runs the mint command in
[`operator-read.md`](operator-read.md) again, or leaves it unset and loses only
a convenience.

## Full rebuild, in order

1. `git clone https://github.com/skymitch9/black-bloc.git` (public — no credentials
   needed) → `access/setup.md` §1.
2. Rebuild `.env` from the tracked `.env.example` (**21** names), pasting each value from
   the 1Password vault **`Black Bloc`**. Re-mint `DISCORD_TOKEN` in the portal
   (`setup.md` §2) if the old one is lost.
3. Restore the DB file if one exists (`%USERPROFILE%\black-bloc-backups\`, newest);
   otherwise start clean — the bot creates schema **34** on first run.
4. Local: `python -m black_bloc`. Hosted: `deploy.md` from "First launch" — which
   recreates the app, the volume and the `[http_service]` block from `fly.toml`.
5. Machine state the clone does NOT carry: re-register the daily backup scheduled task,
   `flyctl auth login`, and re-mint `OPERATOR_READ_TOKEN` if a session needs live reads
   ([`operator-read.md`](operator-read.md)).

⚠️ **Steps 3–5 have never been drilled** — see the Drill log.

## Drill log

*(the log was empty until 2026-09-11; these two entries were transcribed from the
procedures already described above, which record what was actually run and when.)*

| Date | What was drilled | Result |
|---|---|---|
| **2026-08-31** | DB backup **pull** by hand — `sqlite3.backup()` on the Fly machine, `ssh sftp get` to `%USERPROFILE%\black-bloc-backups\`, delete the temp file. The full commands are in "DB backup — the drilled procedure" above | ✅ **PASSED.** Backup written and pulled; verified by opening the pulled file and counting rows (birthdays **38**). Gotchas found and kept: a raw copy can tear (WAL), the image has no `sqlite3` CLI but has `python3`, Git Bash needs `MSYS_NO_PATHCONV=1`, and `flyctl ssh console -C` can exit "The handle is invalid" on Windows *after* the command ran |
| **2026-09-01** | The same thing **as the scheduled task** — "BlackBloc DB backup", daily 04:00, `scripts/backup_db.ps1`, end to end | ✅ **PASSED.** **311,296 bytes** pulled, `ok` logged to `backup.log`. ⚠️ Residual: it runs only while that one machine exists and is signed into flyctl — a silent stop is the failure mode, so check `backup.log` if in doubt |

⚠️ **Never drilled:** a RESTORE (nothing has ever been rebuilt from a backup), a
`git clone`-from-nothing rebuild, re-minting `DISCORD_TOKEN`, recreating the Fly app or
the volume from `fly.toml`, and the 1Password `.env` reconstruction on a second machine.
Every claim about those is inference, and is labelled as such wherever it appears.
