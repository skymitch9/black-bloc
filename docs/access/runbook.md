# Runbook — day-to-day operation of Black Bloc

> **Audience:** the owner (also away from the machine) and Claude sessions. **Status:** TRACKED
> (owner, 2026-08-31 — permanently; the purge-vs-keep question is settled, `docs/` stays in git).
> Secret NAMES only. Last verified: **2026-08-31** — the schema version, the mock page/route counts and the
> synced-command count in the boot sequence were re-measured today (`SCHEMA_VERSION` = 16;
> `node site/mock/check.mjs` = 17 pages / 89 routes; `deploys.log` last line = 35 commands at
> 2026-08-27 20:15). ⚠️ **NOT re-measured today:** the flyctl commands, the machine/volume ids, the
> failure table and the laptop steps — those are the 2026-08-27 reading, and the phone-side steps
> (Discord app) are what the owner did, not measured by Claude.

## Where everything is

| Thing | Where |
|---|---|
| Bot process | Fly.io app `black-bloc`, machine `85e744c4d959d8`, region `lax`, volume `black_bloc_data` at `/data` |
| Database | SQLite `/data/black_bloc.sqlite3` on that volume (schema **19** — `black_bloc/storage/db.py:SCHEMA_VERSION`; 17 `sessions`, 18 `polls.vote_scheme` (2026-08-31), 19 `golive_sessions.live_role_id` (2026-09-01)) |
| Dashboard | https://blackbloc.heygabi.ai (same Fly app; Discord sign-in; staff roles = roles that can see `#mute-me-bot-test-spam`) |
| Health | https://blackbloc.heygabi.ai/health (public JSON: `ok`, `ready`, `guilds`, `latency_ms`) — and the dashboard's **Health** tab (loops, last 50 actions) |
| Logs | `flyctl logs --app black-bloc --no-tail` (below), the dashboard **Logs/Audit** tab, and `/<feature> logs` in Discord (Phase 12, live since 2026-08-27 18:38) |
| Test policy | `TEST_MODE=true`: the bot speaks only in `#mute-me-bot-test-spam` + DMs + the temp-voice channels it created. Owner lifts it (Fly secret), never Claude |
| Code | GitHub `skymitch9/black-bloc` (private), branch `main`; every deploy line in [`../deploys.log`](../deploys.log) |

## The flyctl binary
The Claude session shells never have `flyctl` on PATH. Always spell it out:

```
"$LOCALAPPDATA/Microsoft/WinGet/Packages/Fly-io.flyctl_Microsoft.Winget.Source_8wekyb3d8bbwe/flyctl.exe"
```
(`winget install --id Fly-io.flyctl` on a new machine; then `flyctl auth login` in an interactive shell.)

## Deploy (owner-authorised for Claude, 2026-08-27)
```
git status --short            # must be empty
.venv/Scripts/python -m pytest -q && .venv/Scripts/python -m ruff check .
node site/mock/server.mjs &  node site/mock/check.mjs      # 17 pages / 89 routes ok (2026-08-31)
git push origin main
<flyctl> deploy --app black-bloc --ha=false --remote-only --yes
curl -s https://blackbloc.heygabi.ai/health
<flyctl> logs --app black-bloc --no-tail | grep -i "logged in\|synced\|error\|traceback" | tail
```
Then ONE line in `docs/deploys.log`: `<ISO> black-bloc <commit> machine=85e744c4d959d8 region=lax by=<who> <note>; verified: <what>`.
A deploy restarts the bot (~10 s offline); expect one Fly proxy "refused connection" line in that window.

## Restart / stop / start
```
<flyctl> machine restart 85e744c4d959d8 --app black-bloc
<flyctl> machine stop    85e744c4d959d8 --app black-bloc     # bot offline, site offline
<flyctl> machine start   85e744c4d959d8 --app black-bloc
```

## Roll back
Every deploy is a commit in `deploys.log`. To roll back: `git checkout <good commit> -- .` is NOT the way
(dirty tree); instead `git revert <bad merge> -m 1` (or `git reset --hard <good>` on a throwaway branch),
push, deploy. Schema migrations are additive-only, so an older build runs against a newer database.

## Reading the logs
```
<flyctl> logs --app black-bloc --no-tail | tail -50
<flyctl> logs --app black-bloc --no-tail | grep -i "error\|traceback"
<flyctl> logs --app black-bloc --no-tail | grep "database:"      # migrations on boot
```
Boot sequence to expect: `database ready` → `loaded cog …` ×14 → `synced 35 app commands` → `logged in as
Black_Bloc#6132` → `birthdays: the daily import …` → `chat: seeded N intent(s)` (first boot per guild only).

## Secrets (names; custody in [`RECOVERY.md`](RECOVERY.md))
`DISCORD_TOKEN`, `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `SESSION_SECRET`, `POLL_VOTE_SECRET` (⚠️ losing it makes polls created under it unvotable — they refuse in words rather than double-count), `TWITCH_CLIENT_ID`,
`TWITCH_CLIENT_SECRET`, `TEST_MODE`, `TEST_CHANNEL_ID`, `DEV_GUILD_ID`, `DATABASE_PATH`.
Set on Fly with `<flyctl> secrets set NAME=value --app black-bloc` (each set restarts the machine);
importing many: write an ASCII file and `cmd /c "<flyctl> secrets import --app black-bloc < file"` — a
PowerShell pipe adds a BOM and the first key is rejected as `﻿KEY`.

## Common failures and what they mean
| Symptom | Cause | Fix |
|---|---|---|
| Dashboard looks old / broken layout after a deploy | (fixed 2026-08-27) assets now stamped `?v=` + `no-cache`; if it recurs, hard-reload once | — |
| "This is for staff" on the dashboard | your roles cannot see the test channel | ask an Admin for the role; the page names the roles |
| `/rolemenu` missing from the slash list | `rolemenu_mode` is off (commands hide when off) | Dashboard → Role menus → switch on |
| A panel/announcement never appears | test mode refused the channel — the log shows `would_*` | expected until TEST_MODE is lifted |
| `tempvoice.panel_failed` in the log | the Bots role lacks Send Messages in that voice channel | grant it |
| `role.changed_by_hand` has no actor | the Bots role lacks View Audit Log | grant it |
| Fly proxy `PU03 unreachable worker host` once | the 6-second restart gap | ignore unless it persists |
| `429` on startup sync | too many restarts in a short time (KI-2) | wait a few minutes |

## Local run (for testing without Fly)
```
.venv/Scripts/python -m black_bloc          # needs .env; TEST_MODE=true there too
node site/mock/server.mjs                   # dashboard against fake data on http://127.0.0.1:8788
```
Stop a leftover mock server on Windows: find the `node` PID on the port (`Get-NetTCPConnection -LocalPort 8788`) and `Stop-Process`.

## Docs bookkeeping
`scripts/doctools/move_done.py "<heading>" <note-file> "<TODO line prefix>" [...]` moves TODO items whole
into DONE with a landing note (append-only, newest first). Every ask goes on `TODO.md` the moment it is
mentioned; finished items move in the session they land.

## Laptop from scratch (what you need while away)
You do NOT need `.env` to deploy — secrets live on Fly. You need it only to run the bot locally.

```
git clone https://github.com/skymitch9/black-bloc.git && cd black-bloc
winget install --id Fly-io.flyctl        # then, in a NEW terminal: flyctl auth login (browser)
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"      # tests fake their own tokens
node --version                            # for site/mock/check.mjs (Node 20+)
```
Deploy = the block under **Deploy** above (`git pull` first). Docs are tracked temporarily, so `docs/` comes with the clone.

**`.env` on another machine, without pasting secrets around:** on the main machine run
`sh scripts/env-lock.sh` in YOUR OWN terminal (it prompts for a passphrase; keep it in your password
manager), commit the resulting `.env.enc`, push. On the laptop: `sh scripts/env-unlock.sh` → writes
`.env` (gitignored). AES-256-CBC with PBKDF2 (600k iterations) via the OpenSSL that ships with Git for
Windows; the passphrase never leaves your head/password manager and Claude never sees the values. If
you rotate a secret, re-run lock and commit the new `.env.enc`. (A Firebase/Firestore store would work
too but would need a service-account key on the laptop — a second secret to protect for no gain.)
Variable NAMES in `.env`: `DISCORD_TOKEN DISCORD_CLIENT_ID DISCORD_CLIENT_SECRET SESSION_SECRET POLL_VOTE_SECRET
TWITCH_CLIENT_ID TWITCH_CLIENT_SECRET DEV_GUILD_ID TEST_MODE TEST_CHANNEL_ID DATABASE_PATH API_ENABLED
API_HOST API_PORT SITE_ORIGIN COMMAND_PREFIX LOG_LEVEL`.
