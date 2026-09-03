# Deploying to Fly.io

> **Audience:** Claude sessions and the owner. **Status:** TRACKED (owner,
> 2026-08-31 — was local-only until then; secret NAMES only).
> Last verified: **2026-09-03** — "Every later deploy" rewritten around `scripts/deploy.ps1`
> (the only path since 2026-09-01) and the detached-run gotcha added from that morning's
> killed deploy; the first-launch sequence below was RUN on
> 2026-08-26, in this order, and the bot logged in from Fly (machine
> `85e744c4d959d8`, region `lax`). The **redeploy** path is now well exercised:
> [`../deploys.log`](../deploys.log) records **37 deploys** (counted 2026-08-31), the last
> `8036918` at **2026-08-27 20:15**. ⚠️ rotate/SFTP/scale commands are still
> from Fly's docs and have NOT been exercised. ⚠️ Only the header was
> re-verified today; the command bodies below were not re-run.
> Hosting decision: Fly.io (owner, 2026-08-26). Rationale:
> [`../info/hosting.md`](../info/hosting.md). Every deploy appends a line to
> [`../deploys.log`](../deploys.log).

## Why Fly

One always-on container running `python -m black_bloc`, holding the Discord
gateway websocket 24/7, with a small persistent disk for SQLite. The owner does
not need to be at a machine. Cost class: `shared-cpu-1x` / 256 MB ≈ $2–4/month
(Fly bills by usage; check the current pricing page, do not trust this number).

## First launch (once)

```powershell
# 1. CLI + login. The winget id is Fly-io.flyctl (NOT flyio.flyctl). New shells
#    have it on PATH as `flyctl`; a shell opened before the install does not.
#    ⚠️ The Claude session shell (Bash tool and `!`) never has it: spell out
#    "$LOCALAPPDATA/Microsoft/WinGet/Packages/Fly-io.flyctl_Microsoft.Winget.Source_8wekyb3d8bbwe/flyctl.exe".
#    Owner authorised Claude to run the deploy itself (2026-08-27).
winget install --id Fly-io.flyctl
flyctl auth login        # needs a REAL terminal window - it refuses Claude's
                         # shell and the `!` prompt ("requires an interactive
                         # terminal"). Open PowerShell and run it there.

# 2. Create the app (deterministic; `fly launch` would rewrite fly.toml)
flyctl apps create black-bloc --org personal

# 3. Persistent disk for /data (SQLite). Must be a real Fly region - there is
#    no `phx`; `lax` is the nearest to Phoenix.
flyctl volumes create black_bloc_data --app black-bloc --region lax --size 1 --yes

# 4. Secrets - NEVER into fly.toml or the image. `secrets import` reads KEY=VALUE
#    lines from stdin, so values never appear on a command line or in a log.
#    From the repo root, feed the four needed lines from .env:
# From PowerShell, DO NOT pipe python straight into flyctl: the pipeline prepends a
# UTF-8 BOM to the first key ("\ufeffDISCORD_TOKEN is not a valid secret name").
# Write an ASCII temp file and redirect it through cmd instead:
python -c "import re;open('secrets.tmp','w',encoding='ascii',newline='\n').write(''.join(l for l in open('.env',encoding='utf-8') if re.match(r'^(DISCORD_TOKEN|DEV_GUILD_ID|TEST_MODE|TEST_CHANNEL_ID|TWITCH_CLIENT_ID|TWITCH_CLIENT_SECRET)=.+',l)))"
cmd /c "flyctl secrets import --app black-bloc --stage < secrets.tmp"; Remove-Item secrets.tmp

# 5. Ship it. --ha=false is REQUIRED: the default creates two machines, which
#    is two bots answering every command twice.
flyctl deploy --app black-bloc --ha=false --remote-only --yes
flyctl logs --app black-bloc --no-tail      # expect "logged in as Black_Bloc#..."
```

`fly.toml` has **no `[http_service]`** on purpose - with one, Fly auto-stops
idle machines and the gateway connection dies with them. Keep `[mounts]`.

## Every later deploy — `scripts/deploy.ps1`, nothing else

```powershell
# From the repo root, tree committed-clean (the script REFUSES a dirty tree, and a
# Dockerfile build ships what is on disk). It runs ruff -> the full test suite ->
# node site/mock/check.mjs -> git push origin main -> flyctl deploy, then appends a
# SKELETON line to docs/deploys.log that you must EDIT (what shipped; verified: what
# was checked) and commit. Escape hatch BLACKBLOC_SKIP_GATE=1 - emergencies only.
.\scripts\deploy.ps1
flyctl logs --app black-bloc --no-tail        # boot log: cogs loaded, "commands synced"
flyctl releases --app black-bloc              # a NEW version number = it landed
```

### ⚠️ "The deploy printed nothing after *Waiting for depot builder*" — run it DETACHED

The script takes **~10 minutes** end to end (measured 2026-09-03: pytest alone 8:27 for
3345 tests, single process). A Claude tool call has a **10-minute ceiling**: when it kills
the wrapper mid-`flyctl deploy`, the orphaned flyctl keeps running with a dead stdout pipe,
sits at "Waiting for depot builder" indefinitely and **makes no release** — the push has
already happened, so `main` is ahead of the machine and nothing says so. Seen 2026-09-03
(pid 34312, ten minutes of silence, `flyctl releases` still on the old version).

From a Claude session, never run the script inside a tool call. Detach it and watch the pid:

```powershell
$log = "<scratchpad>\deploy.log"
$p = Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy.ps1" `
       -WorkingDirectory (Get-Location) -RedirectStandardOutput $log -RedirectStandardError "$log.err" `
       -PassThru -WindowStyle Hidden
$p.Id                     # watch this with the Monitor tool; peek with Get-Content $log -Tail 5
```

If a run was already killed: `Stop-Process` the orphaned `flyctl` (`Get-Process flyctl`),
confirm `flyctl releases` shows no new version, and relaunch detached — the tree is still
clean and the push is idempotent. A bare `flyctl deploy` by hand is NOT the fallback; it
skips the gate.

**Never run the bot locally while the Fly machine is up** - two instances
answer every command twice. Pause Fly first: `flyctl machine stop 85e744c4d959d8
--app black-bloc`, then `... start` after.

## Useful

| Need | Command |
|---|---|
| Is it up? | `fly status` |
| Live log tail | `fly logs` |
| Rotate the token | Portal → Reset Token → `fly secrets set DISCORD_TOKEN=...` (redeploys automatically) |
| Shell into the machine | `fly ssh console` |
| Copy the DB out | `fly ssh sftp get /data/black_bloc.sqlite3 .\backup.sqlite3` |
| Pause the bot | `flyctl machine stop <id> --app black-bloc` / `start` |
| Stop paying | `fly scale count 0` (keeps the app + volume), `fly apps destroy black-bloc` (does not) |

## Alternatives considered

See [`../info/hosting.md`](../info/hosting.md). Short version: Railway is
equivalent; a $4–6/mo VPS is fine but adds patching duty; Cloudflare Workers
cannot host this bot at all.
